"""评价任务接口：创建后通过 FastAPI BackgroundTasks 执行多 Agent 工作流。"""
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_evaluation_task
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.evaluation import AgentRunResponse, EvaluationResponse, RetrievalLogResponse
from app.services.evaluation_service import (
    create_evaluation,
    execute_evaluation,
    get_evaluation_detail,
    list_evaluations,
)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("", response_model=ApiResponse[PageData[EvaluationResponse]])
def get_evaluations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    essay_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[PageData[EvaluationResponse]]:
    return success(list_evaluations(db, current_user, page, page_size, essay_id))


@router.post("/{essay_id}", response_model=ApiResponse[EvaluationResponse], status_code=status.HTTP_201_CREATED)
def submit_evaluation(
    essay_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[EvaluationResponse]:
    data = create_evaluation(db, current_user, essay_id)
    background_tasks.add_task(run_evaluation_task, data.id)
    return success(data, message="评价任务已创建并进入后台执行队列")


@router.post("/{evaluation_id}/execute", response_model=ApiResponse[EvaluationResponse])
def start_evaluation(
    evaluation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[EvaluationResponse]:
    data = execute_evaluation(db, current_user, evaluation_id)
    background_tasks.add_task(run_evaluation_task, evaluation_id)
    return success(data, message="评价任务已启动，请轮询最新状态")


@router.get("/{evaluation_id}", response_model=ApiResponse[EvaluationResponse])
def get_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[EvaluationResponse]:
    return success(get_evaluation_detail(db, current_user, evaluation_id))


@router.get("/{evaluation_id}/runs", response_model=ApiResponse[list[AgentRunResponse]])
def get_agent_runs(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[AgentRunResponse]]:
    return success(get_evaluation_detail(db, current_user, evaluation_id).agent_runs)


@router.get("/{evaluation_id}/retrievals", response_model=ApiResponse[list[RetrievalLogResponse]])
def get_retrievals(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[RetrievalLogResponse]]:
    return success(get_evaluation_detail(db, current_user, evaluation_id).retrievals)