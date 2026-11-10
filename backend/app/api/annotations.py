"""作文图片标注接口：只读查看为主，教师/管理员可新增标注。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.annotation import AnnotationCreate, AnnotationResponse
from app.schemas.common import ApiResponse, success
from app.services import annotation_service

router = APIRouter(tags=["essay-annotations"])
teacher_only = require_roles(UserRole.TEACHER, UserRole.ADMIN)


@router.get("/essays/{essay_id}/annotations", response_model=ApiResponse[list[AnnotationResponse]])
def list_annotations(
    essay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[AnnotationResponse]]:
    return success(annotation_service.list_annotations(db, current_user, essay_id))


@router.post(
    "/essays/{essay_id}/annotations",
    response_model=ApiResponse[AnnotationResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_annotation(
    essay_id: int,
    payload: AnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[AnnotationResponse]:
    return success(
        annotation_service.create_annotation(db, current_user, essay_id, payload),
        message="标注已保存，AI 标注与教师标注分轨保留",
    )