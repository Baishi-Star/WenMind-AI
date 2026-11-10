"""作文业务：题目、草稿、提交、编辑、历史与归属校验。"""
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import BASE_DIR, settings
from app.core.exceptions import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.core.logging import get_logger
from app.models.base import EssayStatus, UserRole
from app.models.essay import Essay, EssayPrompt
from app.models.user import User
from app.schemas.common import PageData
from app.schemas.essay import (
    EssayCreate,
    EssayDetail,
    EssayListItem,
    EssayOcrResponse,
    EssayPromptResponse,
    EssayUpdate,
)
from app.services import ocr_service
from app.services.access_service import accessible_student_ids, assert_student_access

logger = get_logger(__name__)

ALLOWED_IMAGE_MIME = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _image_dir() -> Path:
    directory = Path(settings.essay_image_dir)
    if not directory.is_absolute():
        directory = BASE_DIR / directory
    directory.mkdir(parents=True, exist_ok=True)
    return directory.resolve()


def detect_image_mime(data: bytes) -> str | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def save_essay_image(data: bytes) -> tuple[str, int]:
    mime = detect_image_mime(data)
    if mime is None:
        raise AppError("仅支持 JPG、PNG、WebP 格式的图片")
    target = _image_dir() / f"{uuid4().hex}{ALLOWED_IMAGE_MIME[mime]}"
    target.write_bytes(data)
    try:
        token = target.relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        token = target.as_posix()
    return token, len(data)


def resolve_image_token(token: str | None) -> Path | None:
    if not token:
        return None
    candidate = Path(token)
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate
    candidate = candidate.resolve()
    directory = _image_dir()
    if directory not in candidate.parents and candidate != directory:
        return None
    if not candidate.is_file():
        return None
    return candidate


def recognize_essay_image(token: str) -> EssayOcrResponse:
    if not ocr_service.is_enabled():
        return EssayOcrResponse(status="disabled", text="", message="当前未启用图片识别，请手动录入正文")
    path = resolve_image_token(token)
    if path is None:
        return EssayOcrResponse(status="failed", text="", message="图片不存在或已失效，请重新上传")
    with path.open("rb") as handle:
        header = handle.read(16)
    mime = detect_image_mime(header) or "image/png"
    try:
        text = ocr_service.recognize(path, mime)
    except ocr_service.OcrFailure:
        return EssayOcrResponse(status="failed", text="", message="识别失败，请重传图片或手动输入正文")
    return EssayOcrResponse(status="parsed", text=text, message="")


def _serialize_list_item(essay: Essay, student_name: str, prompt_title: str | None) -> EssayListItem:
    return EssayListItem(
        id=essay.id,
        student_id=essay.student_id,
        student_name=student_name,
        prompt_id=essay.prompt_id,
        prompt_title=prompt_title,
        content_version=essay.content_version,
        char_count=essay.char_count,
        status=essay.status,
        is_demo=essay.is_demo,
        source_type=essay.source_type or "text",
        image_path=essay.image_path,
        ocr_status=essay.ocr_status or "none",
        created_at=essay.created_at,
        updated_at=essay.updated_at,
    )


def list_prompts(db: Session) -> list[EssayPromptResponse]:
    prompts = db.scalars(select(EssayPrompt).order_by(EssayPrompt.id)).all()
    return [EssayPromptResponse.model_validate(prompt) for prompt in prompts]


def list_essays(db: Session, user: User, page: int, page_size: int, status: str | None = None) -> PageData[EssayListItem]:
    conditions = []
    student_ids = accessible_student_ids(db, user)
    if student_ids is not None:
        conditions.append(Essay.student_id.in_(student_ids or [-1]))
    if status:
        conditions.append(Essay.status == status)
    total = db.scalar(select(func.count(Essay.id)).where(*conditions)) or 0
    statement = (
        select(Essay, User.display_name, EssayPrompt.title)
        .join(User, Essay.student_id == User.id)
        .outerjoin(EssayPrompt, Essay.prompt_id == EssayPrompt.id)
        .where(*conditions)
        .order_by(Essay.created_at.desc(), Essay.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(statement).all()
    return PageData(
        items=[_serialize_list_item(essay, student_name, prompt_title) for essay, student_name, prompt_title in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def _validate_prompt(db: Session, prompt_id: int | None) -> None:
    if prompt_id is not None and db.get(EssayPrompt, prompt_id) is None:
        raise NotFoundError("作文题目不存在")


def _validate_content(content: str) -> None:
    if len(content) > settings.essay_max_chars:
        raise AppError(f"作文正文不能超过 {settings.essay_max_chars} 字，当前为 {len(content)} 字")


def create_essay(db: Session, user: User, payload: EssayCreate) -> Essay:
    _validate_content(payload.content)
    _validate_prompt(db, payload.prompt_id)
    source_type = payload.source_type or "text"
    image_path = payload.image_path
    ocr_status = "none"
    if source_type == "image":
        resolved = resolve_image_token(image_path)
        if resolved is None:
            logger.warning("图片作文的图片文件丢失，已降级为文本提交 student_id=%s", user.id)
            source_type = "text"
            image_path = None
        elif payload.ocr_text and payload.ocr_text.strip():
            ocr_status = "parsed"
    essay = Essay(
        student_id=user.id,
        prompt_id=payload.prompt_id,
        content=payload.content,
        content_version=1,
        char_count=len(payload.content),
        status=EssayStatus.DRAFT if payload.submission_mode == "draft" else EssayStatus.SUBMITTED,
        is_demo=user.is_demo,
        source_type=source_type,
        image_path=image_path,
        ocr_status=ocr_status,
        ocr_text=payload.ocr_text,
    )
    db.add(essay)
    db.commit()
    db.refresh(essay)
    return essay


def update_essay(db: Session, user: User, essay_id: int, payload: EssayUpdate) -> Essay:
    essay = get_essay_entity(db, user, essay_id)
    if user.role != UserRole.STUDENT or essay.student_id != user.id:
        raise PermissionDeniedError("只能修改本人的作文")
    if essay.status != EssayStatus.DRAFT:
        raise ConflictError("只有草稿可以编辑；已提交作文的评价历史保持不变")
    _validate_content(payload.content)
    _validate_prompt(db, payload.prompt_id)
    if essay.content != payload.content:
        essay.content_version += 1
    essay.prompt_id = payload.prompt_id
    essay.content = payload.content
    essay.char_count = len(payload.content)
    essay.status = EssayStatus.SUBMITTED if payload.submission_mode == "submit" else EssayStatus.DRAFT
    db.commit()
    db.refresh(essay)
    return essay


def get_essay_entity(db: Session, user: User, essay_id: int) -> Essay:
    essay = db.get(Essay, essay_id)
    if essay is None:
        raise NotFoundError("作文不存在")
    assert_student_access(db, user, essay.student_id)
    return essay


def get_essay_detail(db: Session, user: User, essay_id: int) -> EssayDetail:
    essay = get_essay_entity(db, user, essay_id)
    student = db.get(User, essay.student_id)
    prompt = db.get(EssayPrompt, essay.prompt_id) if essay.prompt_id else None
    base = _serialize_list_item(essay, student.display_name, prompt.title if prompt else None)
    return EssayDetail(**base.model_dump(), content=essay.content)