"""评价任务业务逻辑：本阶段仅创建 pending 任务，Agent 执行在后续阶段接入。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.base import EssayStatus, EvaluationStatus
from app.models.evaluation import DimensionScore, Evaluation
from app.models.rubric import RubricVersion
from app.models.user import User
from app.schemas.evaluation import DimensionScoreResponse, EvaluationResponse
from app.services.essay_service import get_essay_entity

DEFAULT_PROMPT_VERSION = "v1.0"
ACTIVE_STATUSES = (EvaluationStatus.PENDING, EvaluationStatus.PROCESSING)


def _select_rubric_id(db: Session, essay) -> int:
    if essay.prompt and essay.prompt.rubric_version_id:
        return essay.prompt.rubric_version_id
    rubric_id = db.scalar(
        select(RubricVersion.id).where(RubricVersion.status == "published").order_by(RubricVersion.id.desc()).limit(1)
    )
    if rubric_id is None:
        raise AppError("当前没有已发布的评分量规，无法创建评价任务")
    return rubric_id


def create_evaluation(db: Session, user: User, essay_id: int) -> EvaluationResponse:
    essay = get_essay_entity(db, user, essay_id)
    active = db.scalar(
        select(Evaluation.id).where(
            Evaluation.essay_id == essay.id,
            Evaluation.status.in_(ACTIVE_STATUSES),
        )
    )
    if active is not None:
        raise ConflictError("该作文已有待处理或处理中的评价任务，请勿重复创建")
    evaluation = Evaluation(
        essay_id=essay.id,
        essay_version=essay.content_version,
        rubric_version_id=_select_rubric_id(db, essay),
        prompt_version=DEFAULT_PROMPT_VERSION,
        status=EvaluationStatus.PENDING,
        is_demo=essay.is_demo,
    )
    essay.status = EssayStatus.EVALUATING
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return get_evaluation_detail(db, user, evaluation.id)


def get_evaluation_detail(db: Session, user: User, evaluation_id: int) -> EvaluationResponse:
    evaluation = db.get(Evaluation, evaluation_id)
    if evaluation is None:
        raise NotFoundError("评价任务不存在")
    get_essay_entity(db, user, evaluation.essay_id)
    dimensions = db.scalars(
        select(DimensionScore).where(DimensionScore.evaluation_id == evaluation.id).order_by(DimensionScore.id)
    ).all()
    return EvaluationResponse(
        id=evaluation.id,
        essay_id=evaluation.essay_id,
        essay_version=evaluation.essay_version,
        rubric_version_id=evaluation.rubric_version_id,
        prompt_version=evaluation.prompt_version,
        original_total_score=evaluation.original_total_score,
        final_total_score=evaluation.final_total_score,
        status=evaluation.status,
        error_message=evaluation.error_message,
        is_demo=evaluation.is_demo,
        created_at=evaluation.created_at,
        updated_at=evaluation.updated_at,
        dimension_scores=[DimensionScoreResponse.model_validate(item) for item in dimensions],
    )