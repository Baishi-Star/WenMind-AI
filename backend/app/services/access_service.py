"""数据归属校验：所有角色权限都必须由后端执行，不能依赖前端隐藏菜单。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import PermissionDeniedError
from app.models.base import UserRole
from app.models.user import ClassRoom, Enrollment, User


def accessible_student_ids(db: Session, user: User) -> list[int] | None:
    """None 表示不限制（管理员）；空列表表示没有任何可见学生。"""
    if user.role == UserRole.ADMIN:
        return None
    if user.role == UserRole.STUDENT:
        return [user.id]
    if user.role == UserRole.TEACHER:
        statement = (
            select(Enrollment.student_id)
            .join(ClassRoom, Enrollment.class_id == ClassRoom.id)
            .where(ClassRoom.teacher_id == user.id)
        )
        return list(db.scalars(statement).all())
    return []


def assert_student_access(db: Session, user: User, student_id: int) -> None:
    allowed_ids = accessible_student_ids(db, user)
    if allowed_ids is not None and student_id not in allowed_ids:
        raise PermissionDeniedError("无权访问该学生的数据")


def assert_class_access(db: Session, user: User, classroom: ClassRoom) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.TEACHER and classroom.teacher_id == user.id:
        return
    if user.role == UserRole.STUDENT:
        enrolled = db.scalar(
            select(Enrollment.id).where(
                Enrollment.class_id == classroom.id,
                Enrollment.student_id == user.id,
            )
        )
        if enrolled is not None:
            return
    raise PermissionDeniedError("无权访问该班级的数据")