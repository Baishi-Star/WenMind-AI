"""作文题目、草稿、提交、编辑与历史接口。"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, require_roles
from app.core.exceptions import AppError, NotFoundError
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.common import ApiResponse, ErrorCode, PageData, success
from app.schemas.essay import (
    EssayCreate,
    EssayDetail,
    EssayImageUploadResponse,
    EssayListItem,
    EssayOcrRequest,
    EssayOcrResponse,
    EssayOcrStatusResponse,
    EssayPromptResponse,
    EssayUpdate,
)
from app.services.essay_service import (
    create_essay,
    get_essay_detail,
    list_essays,
    list_prompts,
    recognize_essay_image,
    resolve_image_token,
    save_essay_image,
    update_essay,
)

router = APIRouter(prefix="/essays", tags=["essays"])
logger = get_logger(__name__)


@router.get("/prompts", response_model=ApiResponse[list[EssayPromptResponse]])
def get_prompts(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ApiResponse[list[EssayPromptResponse]]:
    return success(list_prompts(db))


@router.get("/ocr/status", response_model=ApiResponse[EssayOcrStatusResponse])
def get_ocr_status(
    _current_user: User = Depends(get_current_user),
) -> ApiResponse[EssayOcrStatusResponse]:
    return success(EssayOcrStatusResponse(enabled=settings.ocr_enabled))


@router.post("/upload-image", response_model=ApiResponse[EssayImageUploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_essay_image(
    image: UploadFile = File(...),
    _current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> ApiResponse[EssayImageUploadResponse]:
    content_type = (image.content_type or "").lower()
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise AppError("仅支持 JPG、PNG、WebP 格式的图片")
    data = await image.read()
    if not data:
        raise AppError("图片内容为空")
    if len(data) > settings.essay_image_max_mb * 1024 * 1024:
        raise AppError(f"图片大小不能超过 {settings.essay_image_max_mb} MB")
    try:
        token, size = save_essay_image(data)
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001 - 保存失败转为可读错误
        logger.exception("作文图片保存失败")
        raise AppError("图片保存失败，请稍后重试", ErrorCode.INTERNAL_ERROR, 500) from exc
    preview_url = f"{settings.api_v1_prefix}/essays/image?token={quote(token)}"
    return success(
        EssayImageUploadResponse(
            image_token=token,
            preview_url=preview_url,
            size_bytes=size,
            ocr_enabled=settings.ocr_enabled,
        ),
        message="图片上传成功",
    )


@router.post("/ocr", response_model=ApiResponse[EssayOcrResponse])
def recognize_essay(
    payload: EssayOcrRequest,
    _current_user: User = Depends(require_roles(UserRole.STUDENT)),
) -> ApiResponse[EssayOcrResponse]:
    return success(recognize_essay_image(payload.image_token))


@router.get("/image")
def get_essay_image(
    token: str = Query(...),
    _current_user: User = Depends(get_current_user),
) -> FileResponse:
    path = resolve_image_token(token)
    if path is None:
        raise NotFoundError("图片不存在")
    return FileResponse(path)


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