"""认证业务逻辑：公开注册仅创建学生，演示教师和管理员仅由受控初始化创建。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
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
    token, expires_in = create_access_token(user.id, user.role)
    return user, token, expires_in