"""认证业务逻辑：公开注册仅创建学生，演示教师和管理员仅由受控初始化创建。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, PermissionDeniedError, UnauthorizedError
from app.core.security import create_access_token, hash_password, needs_rehash, verify_password
from app.models.base import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


def register_user(db: Session, payload: RegisterRequest) -> User:
    existing = db.scalar(select(User).where(User.username == payload.username))
    if existing:
        raise ConflictError("用户名已存在")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        role=UserRole.STUDENT,
        status="active",
        is_demo=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: LoginRequest) -> tuple[User, str, int]:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("用户名或密码错误")
    if user.status != "active":
        raise UnauthorizedError("账号已被停用")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()
    token, expires_in = create_access_token(user.id, user.role)
    return user, token, expires_in

DEMO_ROLE_USERNAMES = {
    "student": "demo_student",
    "teacher": "demo_teacher",
    "admin": "demo_admin",
}


def list_demo_users(db: Session) -> list[User]:
    """按学生、教师、管理员顺序返回各角色首个演示账号。"""
    users: list[User] = []
    for role in ("student", "teacher", "admin"):
        preferred = DEMO_ROLE_USERNAMES[role]
        user = db.scalar(
            select(User)
            .where(User.role == role, User.is_demo.is_(True))
            .order_by((User.username == preferred).desc(), User.id)
        )
        if user is not None:
            users.append(user)
    return users


def demo_login(db: Session, role: str) -> tuple[User, str, int]:
    if not settings.demo_login_enabled:
        raise PermissionDeniedError("演示登录已关闭")
    preferred = DEMO_ROLE_USERNAMES.get(role)
    if preferred is None:
        raise UnauthorizedError("不支持的演示角色")
    user = db.scalar(
        select(User)
        .where(User.role == role, User.is_demo.is_(True))
        .order_by((User.username == preferred).desc(), User.id)
    )
    if user is None:
        raise UnauthorizedError("演示账号不存在或未初始化")
    if not settings.demo_password:
        raise UnauthorizedError("未配置演示密码，请设置 DEMO_PASSWORD")
    if not verify_password(settings.demo_password, user.password_hash):
        raise UnauthorizedError("演示密码与账号不匹配，请检查 DEMO_PASSWORD")
    if user.status != "active":
        raise UnauthorizedError("账号已被停用")
    token, expires_in = create_access_token(user.id, user.role)
    return user, token, expires_in