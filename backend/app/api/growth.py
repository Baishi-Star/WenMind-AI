"""成长画像、训练任务与教师班级分析接口。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.growth import (
    ClassAnalyticsResponse,
    GrowthHistoryResponse,
    GrowthProfileResponse,
    TrainingCompleteRequest,
    TrainingTaskListResponse,
    TrainingTaskResponse,
)
from app.services.class_analytics_service import get_class_analytics
from app.services.growth_service import (
    complete_training_task,
    ensure_training_tasks,
    get_history,
    get_profile,
)

router = APIRouter(tags=["growth"])


@router.get("/growth/profile", response_model=ApiResponse[GrowthProfileResponse])
def profile(
    student_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[GrowthProfileResponse]:
    return success(get_profile(db, current_user, student_id))


@router.get("/growth/history", response_model=ApiResponse[GrowthHistoryResponse])
def history(
    student_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[GrowthHistoryResponse]:
    return success(get_history(db, current_user, student_id))


@router.get("/training/tasks", response_model=ApiResponse[TrainingTaskListResponse])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> ApiResponse[TrainingTaskListResponse]:
    return success(ensure_training_tasks(db, current_user))


@router.post("/training/tasks/{task_id}/complete", response_model=ApiResponse[TrainingTaskResponse])
def complete_task(
    task_id: int,
    payload: TrainingCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> ApiResponse[TrainingTaskResponse]:
    return success(complete_training_task(db, current_user, task_id, payload.result_text), message="训练任务已完成并保存结果")


@router.get("/teacher/classes/{class_id}/analytics", response_model=ApiResponse[ClassAnalyticsResponse])
def class_analytics(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
) -> ApiResponse[ClassAnalyticsResponse]:
    return success(get_class_analytics(db, current_user, class_id))