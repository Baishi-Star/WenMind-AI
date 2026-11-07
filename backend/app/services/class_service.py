"""班级业务逻辑与班级归属校验。"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.base import UserRole
from app.models.user import ClassRoom, Enrollment, User
from app.schemas.classroom import ClassCreate, ClassResponse
from app.services.access_service import assert_class_access


def _serialize_class(db: Session, classroom: ClassRoom) -> ClassResponse:
    teacher = db.get(User, classroom.teacher_id)
    student_count = db.scalar(
        select(func.count(Enrollment.id)).where(Enrollment.class_id == classroom.id)
    ) or 0
    return ClassResponse(
        id=classroom.id,
        name=classroom.name,
        teacher_id=classroom.teacher_id,
        teacher_name=teacher.display_name,
        student_count=student_count,
        is_demo=classroom.is_demo,
        created_at=classroom.created_at,
    )


def list_classes(db: Session, user: User) -> list[ClassResponse]:
    statement = select(ClassRoom)
    if user.role == UserRole.TEACHER:
        statement = statement.where(ClassRoom.teacher_id == user.id)
    elif user.role == UserRole.STUDENT:
        statement = statement.join(Enrollment, Enrollment.class_id == ClassRoom.id).where(
            Enrollment.student_id == user.id
        )
    classes = db.scalars(statement.order_by(ClassRoom.created_at.desc())).all()
    return [_serialize_class(db, classroom) for classroom in classes]


def create_class(db: Session, user: User, payload: ClassCreate) -> ClassResponse:
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise PermissionDeniedError("只有教师或管理员可以创建班级")
    teacher_id = payload.teacher_id or user.id
    if user.role == UserRole.TEACHER and teacher_id != user.id:
        raise PermissionDeniedError("教师只能创建本人负责的班级")
    teacher = db.get(User, teacher_id)
    if teacher is None or teacher.role != UserRole.TEACHER:
        raise NotFoundError("负责教师不存在或角色不正确")
    classroom = ClassRoom(name=payload.name.strip(), teacher_id=teacher_id, is_demo=user.is_demo)
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return _serialize_class(db, classroom)


def get_class_detail(db: Session, user: User, class_id: int) -> ClassResponse:
    classroom = db.get(ClassRoom, class_id)
    if classroom is None:
        raise NotFoundError("班级不存在")
    assert_class_access(db, user, classroom)
    return _serialize_class(db, classroom)