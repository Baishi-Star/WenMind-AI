"""作文图片标注服务：AI 证据框与教师批注，坐标归一化，双轨保存。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.annotation import AnnotationShape, AnnotationSource, EssayAnnotation
from app.models.base import UserRole
from app.models.essay import Essay
from app.models.submission import SubmissionAnswer
from app.models.user import User
from app.schemas.annotation import AnnotationCreate, AnnotationResponse


def _assert_essay_access(db: Session, user: User, essay: Essay) -> None:
    if user.role == UserRole.STUDENT:
        if essay.student_id != user.id:
            raise PermissionDeniedError("无权访问该作文")
        return
    if user.role == UserRole.TEACHER:
        from app.services.access_service import assert_student_access

        assert_student_access(db, user, essay.student_id)
        return
    if user.role == UserRole.ADMIN:
        return
    raise PermissionDeniedError("无权访问该作文")


def _serialize(record: EssayAnnotation) -> AnnotationResponse:
    return AnnotationResponse(
        id=record.id,
        essay_id=record.essay_id,
        submission_file_id=record.submission_file_id,
        source=record.source,
        label=record.label,
        shape=record.shape,
        x=record.x,
        y=record.y,
        width=record.width,
        height=record.height,
        page_no=record.page_no,
        note=record.note,
        color=record.color,
        feedback_item_id=record.feedback_item_id,
        created_at=record.created_at,
    )


def list_annotations(db: Session, user: User, essay_id: int) -> list[AnnotationResponse]:
    essay = db.get(Essay, essay_id)
    if essay is None:
        raise NotFoundError("作文不存在")
    _assert_essay_access(db, user, essay)
    records = db.scalars(
        select(EssayAnnotation)
        .where(EssayAnnotation.essay_id == essay_id)
        .order_by(EssayAnnotation.page_no, EssayAnnotation.id)
    ).all()
    return [_serialize(item) for item in records]


def create_annotation(
    db: Session, user: User, essay_id: int, payload: AnnotationCreate
) -> AnnotationResponse:
    """新增标注：第一版仅教师/管理员可写，教师标注不覆盖 AI 标注。"""
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise PermissionDeniedError("只有教师或管理员可以新增图片标注")
    essay = db.get(Essay, essay_id)
    if essay is None:
        raise NotFoundError("作文不存在")
    _assert_essay_access(db, user, essay)
    if payload.submission_file_id is not None:
        from app.models.submission import SubmissionFile

        record = db.get(SubmissionFile, payload.submission_file_id)
        if record is None:
            raise NotFoundError("图片不存在")
        answer = db.scalar(select(SubmissionAnswer).where(SubmissionAnswer.essay_id == essay_id))
        if answer is None or answer.submission_id != record.submission_id:
            raise PermissionDeniedError("该图片不属于此作文")
    annotation = EssayAnnotation(
        essay_id=essay_id,
        submission_file_id=payload.submission_file_id,
        source=AnnotationSource.TEACHER,
        label=payload.label,
        shape=payload.shape,
        x=payload.x,
        y=payload.y,
        width=payload.width,
        height=payload.height,
        page_no=payload.page_no,
        note=payload.note,
        color=payload.color,
        created_by=user.id,
        is_readonly=True,
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return _serialize(annotation)