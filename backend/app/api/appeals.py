"""学生申诉提交与进度查询接口。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.interaction import AppealCreate, AppealResponse
from app.services.appeal_service import create_appeal, get_appeal_detail, list_appeals

router = APIRouter(prefix="/appeals", tags=["appeals"])


@router.post("", response_model=ApiResponse[AppealResponse], status_code=status.HTTP_201_CREATED)
def submit_appeal(
    payload: AppealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> ApiResponse[AppealResponse]:
    return success(create_appeal(db, current_user, payload), message="申诉已提交，等待教师复核；不会自动改分")


@router.get("", response_model=ApiResponse[list[AppealResponse]])
def get_appeals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[AppealResponse]]:
    return success(list_appeals(db, current_user))


@router.get("/{appeal_id}", response_model=ApiResponse[AppealResponse])
def get_appeal(
    appeal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[AppealResponse]:
    return success(get_appeal_detail(db, current_user, appeal_id))