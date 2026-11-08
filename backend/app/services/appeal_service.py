"""学生申诉：关联评价项、原文证据并记录处理状态，不自动改分。"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.evidence import verify_evidence_item
from app.core.exceptions import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.models.appeal import Appeal, ReviewRecord
from app.models.base import EvaluationStatus, UserRole
from app.models.essay import Essay
from app.models.evaluation import Evaluation, FeedbackItem
from app.models.student_interaction import AppealItem
from app.models.user import User
from app.schemas.agent import EvidenceItem
from app.schemas.interaction import AppealCreate, AppealItemResponse, AppealResponse
from app.services.access_service import accessible_student_ids, assert_student_access
from app.services.essay_service import get_essay_entity

ALLOWED_REASONS = {
    "score_low",
    "evidence_mismatch",
    "intent_misunderstood",
    "creative_expression_misjudged",
    "missed_strength",
    "rubric_disagreement",
    "other",
}
ACTIVE_STATUSES = ("pending", "reviewing")


def _loads(value: str | None) -> list:
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return []


def _serialize_appeal(db: Session, appeal: Appeal) -> AppealResponse:
    evaluation = db.get(Evaluation, appeal.evaluation_id)
    items = db.scalars(select(AppealItem).where(AppealItem.appeal_id == appeal.id).order_by(AppealItem.id)).all()
    reviews = db.scalars(select(ReviewRecord).where(ReviewRecord.appeal_id == appeal.id).order_by(ReviewRecord.id)).all()
    return AppealResponse(
        id=appeal.id,
        evaluation_id=appeal.evaluation_id,
        essay_id=evaluation.essay_id,
        student_id=appeal.student_id,
        reason_type=appeal.reason_type,
        dimension=appeal.dimension,
        description=appeal.description,
        status=appeal.status,
        submitted_at=appeal.submitted_at,
        items=[
            AppealItemResponse(
                id=item.id,
                feedback_item_id=item.feedback_item_id,
                student_note=item.student_note,
                evidence=[EvidenceItem.model_validate(entry) for entry in _loads(item.evidence_location_json)],
            )
            for item in items
        ],
        review_records=[
            {
                "decision": review.decision,
                "review_comment": review.review_comment,
                "reviewed_at": review.reviewed_at,
            }
            for review in reviews
        ],
    )


def create_appeal(db: Session, user: User, payload: AppealCreate) -> AppealResponse:
    evaluation = db.get(Evaluation, payload.evaluation_id)
    if evaluation is None:
        raise NotFoundError("评价任务不存在")
    essay = get_essay_entity(db, user, evaluation.essay_id)
    if user.role != UserRole.STUDENT or essay.student_id != user.id:
        raise PermissionDeniedError("只能对本人的作文评价提交申诉")
    if evaluation.status != EvaluationStatus.COMPLETED:
        raise ConflictError("评价完成后才能提交申诉")
    if payload.reason_type not in ALLOWED_REASONS:
        raise AppError("申诉原因不在允许范围内")
    if payload.dimension not in {"content", "organization", "language", "overall", "topic"}:
        raise AppError("争议维度不正确")
    active = db.scalar(
        select(Appeal.id).where(
            Appeal.evaluation_id == evaluation.id,
            Appeal.student_id == user.id,
            Appeal.status.in_(ACTIVE_STATUSES),
        )
    )
    if active is not None:
        raise ConflictError("本次评价已有正在处理的申诉，请勿重复提交")
    feedback = None
    if payload.feedback_item_id is not None:
        feedback = db.get(FeedbackItem, payload.feedback_item_id)
        if feedback is None or feedback.evaluation_id != evaluation.id:
            raise NotFoundError("关联评价项不存在")
    if payload.evidence is not None:
        evidence = [verify_evidence_item(payload.evidence, essay.content)]
        if evidence[0].verified_status != "verified":
            raise AppError("申诉引用的原文未通过核验，请从作文原文中选择证据")
    elif feedback is not None:
        evidence = [EvidenceItem.model_validate(item) for item in _loads(feedback.evidence_json)]
    else:
        evidence = []
    appeal = Appeal(
        evaluation_id=evaluation.id,
        student_id=user.id,
        reason_type=payload.reason_type,
        dimension=payload.dimension,
        description=payload.description.strip(),
        status="pending",
    )
    db.add(appeal)
    db.flush()
    db.add(
        AppealItem(
            appeal_id=appeal.id,
            feedback_item_id=feedback.id if feedback else None,
            student_note=payload.description.strip(),
            evidence_location_json=json.dumps([item.model_dump() for item in evidence], ensure_ascii=False),
        )
    )
    db.commit()
    return _serialize_appeal(db, appeal)


def list_appeals(db: Session, user: User) -> list[AppealResponse]:
    conditions = []
    student_ids = accessible_student_ids(db, user)
    if student_ids is not None:
        conditions.append(Appeal.student_id.in_(student_ids or [-1]))
    appeals = db.scalars(select(Appeal).where(*conditions).order_by(Appeal.submitted_at.desc(), Appeal.id.desc())).all()
    return [_serialize_appeal(db, appeal) for appeal in appeals]


def get_appeal_detail(db: Session, user: User, appeal_id: int) -> AppealResponse:
    appeal = db.get(Appeal, appeal_id)
    if appeal is None:
        raise NotFoundError("申诉记录不存在")
    assert_student_access(db, user, appeal.student_id)
    return _serialize_appeal(db, appeal)