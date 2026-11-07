"""班级查询与创建接口。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.classroom import ClassCreate, ClassResponse
from app.schemas.common import ApiResponse, success
from app.services.class_service import create_class, get_class_detail, list_classes

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get("", response_model=ApiResponse[list[ClassResponse]])
def get_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[ClassResponse]]:
    return success(list_classes(db, current_user))


@router.post("", response_model=ApiResponse[ClassResponse], status_code=status.HTTP_201_CREATED)
def submit_class(
    payload: ClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
) -> ApiResponse[ClassResponse]:
    return success(create_class(db, current_user, payload), message="班级创建成功")


@router.get("/{class_id}", response_model=ApiResponse[ClassResponse])
def get_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ClassResponse]:
    return success(get_class_detail(db, current_user, class_id))