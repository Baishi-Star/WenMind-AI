"""教师申诉工作台、人工复核与争议统计接口。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.teacher import (
    AppealPatternStats,
    TeacherAppealDetail,
    TeacherAppealListItem,
    TeacherReviewRequest,
    TeacherReviewResponse,
)
from app.services.teacher_review_service import appeal_pattern_stats, get_appeal_detail, list_appeals, review_appeal

router = APIRouter(prefix="/teacher", tags=["teacher-reviews"])
teacher_only = require_roles(UserRole.TEACHER, UserRole.ADMIN)


@router.get("/appeals", response_model=ApiResponse[list[TeacherAppealListItem]])
def get_appeals(
    class_id: int | None = Query(default=None, gt=0),
    appeal_status: str | None = Query(default=None, alias="status"),
    reason_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[list[TeacherAppealListItem]]:
    return success(list_appeals(db, current_user, class_id, appeal_status, reason_type))


@router.get("/appeals/{appeal_id}", response_model=ApiResponse[TeacherAppealDetail])
def get_appeal(
    appeal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[TeacherAppealDetail]:
    return success(get_appeal_detail(db, current_user, appeal_id))


@router.post("/appeals/{appeal_id}/review", response_model=ApiResponse[TeacherReviewResponse])
def submit_review(
    appeal_id: int,
    payload: TeacherReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[TeacherReviewResponse]:
    data = review_appeal(db, current_user, appeal_id, payload)
    return success(data, message="复核结果已保存，AI 原始评价未被覆盖")


@router.get("/analytics/appeal-patterns", response_model=ApiResponse[AppealPatternStats])
def get_appeal_patterns(
    days: int = Query(default=30, ge=1, le=365),
    class_id: int | None = Query(default=None, gt=0),
    dimension: str | None = Query(default=None),
    tag_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[AppealPatternStats]:
    return success(appeal_pattern_stats(db, current_user, days, class_id, dimension, tag_code))