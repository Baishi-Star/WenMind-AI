"""评价任务接口：仅创建和查询真实任务状态，不伪造 AI 完成结果。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.evaluation import EvaluationResponse
from app.services.evaluation_service import create_evaluation, get_evaluation_detail

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("/{essay_id}", response_model=ApiResponse[EvaluationResponse], status_code=status.HTTP_201_CREATED)
def submit_evaluation(
    essay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[EvaluationResponse]:
    data = create_evaluation(db, current_user, essay_id)
    return success(data, message="评价任务已创建，当前状态为 pending")


@router.get("/{evaluation_id}", response_model=ApiResponse[EvaluationResponse])
def get_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[EvaluationResponse]:
    return success(get_evaluation_detail(db, current_user, evaluation_id))