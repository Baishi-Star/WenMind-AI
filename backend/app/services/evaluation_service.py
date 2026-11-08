"""评价任务业务：创建、执行、列表以及 Agent/RAG/综合报告查询。"""
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.agent_evaluation import EvaluationReport, RetrievalLog
from app.models.base import EssayStatus, EvaluationStatus
from app.models.essay import Essay
from app.models.evaluation import AgentRun, DimensionScore, Evaluation
from app.models.rubric import RubricVersion
from app.models.user import User
from app.schemas.common import PageData
from app.schemas.evaluation import (
    AgentRunResponse,
    DimensionScoreResponse,
    EvaluationReportResponse,
    EvaluationResponse,
    RetrievalLogResponse,
)
from app.services.access_service import accessible_student_ids
from app.services.essay_service import get_essay_entity

DEFAULT_PROMPT_VERSION = "agent-prompt-v1.0"
ACTIVE_STATUSES = (EvaluationStatus.PENDING, EvaluationStatus.PROCESSING)


def _loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _select_rubric_id(db: Session, essay: Essay) -> int:
    if essay.prompt and essay.prompt.rubric_version_id:
        return essay.prompt.rubric_version_id
    rubric_id = db.scalar(
        select(RubricVersion.id).where(RubricVersion.status == "published").order_by(RubricVersion.id.desc()).limit(1)
    )
    if rubric_id is None:
        raise AppError("当前没有已发布的评分量规，无法创建评价任务")
    return rubric_id


def _get_evaluation_entity(db: Session, user: User, evaluation_id: int) -> Evaluation:
    evaluation = db.get(Evaluation, evaluation_id)
    if evaluation is None:
        raise NotFoundError("评价任务不存在")
    get_essay_entity(db, user, evaluation.essay_id)
    return evaluation


def _serialize_run(run: AgentRun) -> AgentRunResponse:
    return AgentRunResponse(
        id=run.id,
        agent_name=run.agent_name,
        model_name=run.model_name,
        prompt_version=run.prompt_version,
        status=run.status,
        latency_ms=run.latency_ms,
        input_summary=_loads(run.input_json, {}),
        output=_loads(run.output_json, None),
        token_usage=_loads(run.token_usage_json, None),
        error_message=run.error_message,
        created_at=run.created_at,
    )


def _serialize_evaluation(db: Session, evaluation: Evaluation, include_details: bool = True) -> EvaluationResponse:
    dimensions = db.scalars(
        select(DimensionScore).where(DimensionScore.evaluation_id == evaluation.id).order_by(DimensionScore.id)
    ).all()
    report_data = None
    runs_data = []
    retrievals_data = []
    if include_details:
        report = db.scalar(select(EvaluationReport).where(EvaluationReport.evaluation_id == evaluation.id))
        if report is not None:
            report_data = EvaluationReportResponse(
                execution_mode=report.execution_mode,
                overall_summary=report.overall_summary,
                quality_status=report.quality_status,
                quality_issues=_loads(report.quality_issues_json, []),
                training_suggestions=_loads(report.training_suggestions_json, []),
                report=_loads(report.report_json, {}),
                started_at=report.started_at,
                completed_at=report.completed_at,
            )
        runs = db.scalars(select(AgentRun).where(AgentRun.evaluation_id == evaluation.id).order_by(AgentRun.id)).all()
        runs_data = [_serialize_run(run) for run in runs]
        retrievals = db.scalars(
            select(RetrievalLog).where(RetrievalLog.evaluation_id == evaluation.id).order_by(RetrievalLog.id)
        ).all()
        retrievals_data = [
            RetrievalLogResponse(
                id=item.id,
                query=item.query,
                search_mode=item.search_mode,
                semantic=item.semantic,
                results=_loads(item.results_json, []),
                created_at=item.created_at,
            )
            for item in retrievals
        ]
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
        report=report_data,
        agent_runs=runs_data,
        retrievals=retrievals_data,
    )


def create_evaluation(db: Session, user: User, essay_id: int) -> EvaluationResponse:
    essay = get_essay_entity(db, user, essay_id)
    active = db.scalar(
        select(Evaluation.id).where(Evaluation.essay_id == essay.id, Evaluation.status.in_(ACTIVE_STATUSES))
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
    return _serialize_evaluation(db, evaluation)


def execute_evaluation(db: Session, user: User, evaluation_id: int) -> EvaluationResponse:
    evaluation = _get_evaluation_entity(db, user, evaluation_id)
    if evaluation.status not in (EvaluationStatus.PENDING, EvaluationStatus.FAILED):
        raise ConflictError("只有待处理或失败的评价任务可以启动执行")
    evaluation.status = EvaluationStatus.PENDING
    evaluation.error_message = None
    db.commit()
    return _serialize_evaluation(db, evaluation)


def get_evaluation_detail(db: Session, user: User, evaluation_id: int) -> EvaluationResponse:
    evaluation = _get_evaluation_entity(db, user, evaluation_id)
    return _serialize_evaluation(db, evaluation)


def list_evaluations(
    db: Session,
    user: User,
    page: int,
    page_size: int,
    essay_id: int | None = None,
) -> PageData[EvaluationResponse]:
    conditions = []
    student_ids = accessible_student_ids(db, user)
    if student_ids is not None:
        conditions.append(Essay.student_id.in_(student_ids or [-1]))
    if essay_id is not None:
        conditions.append(Evaluation.essay_id == essay_id)
    join_condition = (Evaluation.essay_id == Essay.id,)
    total = db.scalar(select(func.count(Evaluation.id)).join(Essay, *join_condition).where(*conditions)) or 0
    evaluations = db.scalars(
        select(Evaluation)
        .join(Essay, *join_condition)
        .where(*conditions)
        .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PageData(
        items=[_serialize_evaluation(db, item, include_details=False) for item in evaluations],
        total=total,
        page=page,
        page_size=page_size,
    )