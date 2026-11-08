"""作文题目、草稿、提交、编辑与历史接口。"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.essay import EssayCreate, EssayDetail, EssayListItem, EssayPromptResponse, EssayUpdate
from app.services.essay_service import create_essay, get_essay_detail, list_essays, list_prompts, update_essay

router = APIRouter(prefix="/essays", tags=["essays"])


@router.get("/prompts", response_model=ApiResponse[list[EssayPromptResponse]])
def get_prompts(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ApiResponse[list[EssayPromptResponse]]:
    return success(list_prompts(db))


@router.get("", response_model=ApiResponse[PageData[EssayListItem]])
def get_essays(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    essay_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[PageData[EssayListItem]]:
    return success(list_essays(db, current_user, page, page_size, essay_status))


@router.post("", response_model=ApiResponse[EssayDetail], status_code=status.HTTP_201_CREATED)
def submit_essay(
    payload: EssayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> ApiResponse[EssayDetail]:
    essay = create_essay(db, current_user, payload)
    message = "草稿保存成功" if payload.submission_mode == "draft" else "作文提交成功"
    return success(get_essay_detail(db, current_user, essay.id), message=message)


@router.put("/{essay_id}", response_model=ApiResponse[EssayDetail])
def edit_essay(
    essay_id: int,
    payload: EssayUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> ApiResponse[EssayDetail]:
    essay = update_essay(db, current_user, essay_id, payload)
    message = "草稿已更新" if payload.submission_mode == "draft" else "草稿已提交"
    return success(get_essay_detail(db, current_user, essay.id), message=message)


@router.get("/{essay_id}", response_model=ApiResponse[EssayDetail])
def get_essay(
    essay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[EssayDetail]:
    return success(get_essay_detail(db, current_user, essay_id))