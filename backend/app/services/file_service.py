"""作文提交文件服务：图片校验、安全存储、页序管理、旋转与受控读取。"""
import hashlib
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import BASE_DIR, settings
from app.core.exceptions import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.models.base import UserRole, utc_now
from app.models.submission import FileKind, Submission, SubmissionAnswer, SubmissionFile
from app.models.user import User
from app.models.writing_task import WritingTask
from app.services import writing_task_service

UPLOAD_DIR = BASE_DIR / "data" / "submission_uploads"

# 通过文件头魔数判断真实类型，不信任用户扩展名。
IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": ("image/jpeg", ".jpg"),
    b"\x89PNG\r\n\x1a\n": ("image/png", ".png"),
    b"RIFF": ("image/webp", ".webp"),
}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def detect_image_type(content: bytes) -> tuple[str, str]:
    """返回 (mime, extension)；仅接受真实图片，拒绝伪装文件。"""
    if len(content) < 12:
        raise AppError("图片内容过小，无法识别为有效图片")
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp", ".webp"
    raise AppError("仅支持 JPG、PNG、WEBP 图片；检测到文件真实内容不是图片")


def _read_dimensions(content: bytes, mime: str) -> tuple[int | None, int | None]:
    """读取图片宽高；缺少 Pillow 或解析失败时不影响上传。"""
    try:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(content)) as image:
            return image.width, image.height
    except Exception:
        return None, None


def _get_submission_for_write(db: Session, student: User, submission_id: int) -> Submission:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise NotFoundError("提交记录不存在")
    if submission.student_id != student.id:
        raise PermissionDeniedError("只能操作本人的提交记录")
    if submission.status not in ("draft", "uploaded", "needs_confirmation", "ready"):
        raise ConflictError("该提交已进入评价流程，不能再修改图片")
    return submission


def list_files(db: Session, submission: Submission) -> list[SubmissionFile]:
    return list(
        db.scalars(
            select(SubmissionFile)
            .where(SubmissionFile.submission_id == submission.id)
            .order_by(SubmissionFile.sort_order, SubmissionFile.id)
        ).all()
    )


def upload_images(
    db: Session,
    student: User,
    submission_id: int,
    uploads: list[tuple[str, bytes]],
    file_kind: str = FileKind.PHOTO,
) -> list[SubmissionFile]:
    """批量上传图片：类型、大小、页数、去重校验后落盘并写入数据库。"""
    if not uploads:
        raise AppError("请至少选择一张图片")
    if file_kind not in FileKind.ALL:
        raise AppError("文件类型不正确")
    submission = _get_submission_for_write(db, student, submission_id)
    existing = list_files(db, submission)
    max_pages = settings.submission_image_max_pages
    if len(existing) + len(uploads) > max_pages:
        raise AppError(f"单个提交最多上传 {max_pages} 页图片，当前已有 {len(existing)} 页")

    single_limit = settings.submission_image_max_mb * 1024 * 1024
    total_limit = settings.submission_image_total_max_mb * 1024 * 1024
    used_total = sum(item.file_size for item in existing)
    existing_hashes = {item.file_hash for item in existing}

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target_dir = UPLOAD_DIR / str(submission.id)
    target_dir.mkdir(parents=True, exist_ok=True)

    next_order = (max((item.sort_order for item in existing), default=0)) + 1
    created: list[SubmissionFile] = []
    for original_filename, content in uploads:
        if not content:
            raise AppError(f"文件「{original_filename}」为空")
        if len(content) > single_limit:
            raise AppError(f"图片「{original_filename}」超过 {settings.submission_image_max_mb} MB 限制")
        if used_total + len(content) > total_limit:
            raise AppError(f"本次提交图片总量超过 {settings.submission_image_total_max_mb} MB 限制")
        mime, extension = detect_image_type(content)
        # 真实格式以魔数为准；扩展名与真实格式不一致时仍按真实格式存储，
        # 只在扩展名明显不属于图片类型时拒绝。
        declared = Path(original_filename or "").suffix.lower()
        if declared and declared not in ALLOWED_EXTENSIONS:
            raise AppError(f"不支持的图片扩展名：{declared}")
        file_hash = hashlib.sha256(content).hexdigest()
        if file_hash in existing_hashes:
            raise ConflictError(f"图片「{original_filename}」与已上传图片重复")
        existing_hashes.add(file_hash)
        stored_path = target_dir / f"{uuid4().hex}{extension}"
        stored_path.write_bytes(content)
        width, height = _read_dimensions(content, mime)
        record = SubmissionFile(
            submission_id=submission.id,
            file_kind=file_kind,
            original_filename=Path(original_filename or "image").name[:255],
            stored_path=str(stored_path),
            mime_type=mime,
            file_size=len(content),
            file_hash=file_hash,
            page_no=next_order,
            sort_order=next_order,
            rotation=0,
            width=width,
            height=height,
            extraction_status="pending",
        )
        db.add(record)
        created.append(record)
        used_total += len(content)
        next_order += 1

    if submission.status == "draft":
        submission.status = "uploaded"
    db.commit()
    for record in created:
        db.refresh(record)
    return created


def delete_file(db: Session, student: User, submission_id: int, file_id: int) -> dict:
    submission = _get_submission_for_write(db, student, submission_id)
    record = db.get(SubmissionFile, file_id)
    if record is None or record.submission_id != submission.id:
        raise NotFoundError("图片不存在")
    stored_path = Path(record.stored_path)
    db.delete(record)
    db.flush()
    for index, item in enumerate(list_files(db, submission), start=1):
        item.sort_order = index
        item.page_no = index
    db.commit()
    stored_path.unlink(missing_ok=True)
    return {"deleted_file_id": file_id}


def reorder_files(db: Session, student: User, submission_id: int, items: list[dict]) -> list[SubmissionFile]:
    submission = _get_submission_for_write(db, student, submission_id)
    records = {item.id: item for item in list_files(db, submission)}
    if not records:
        raise AppError("当前提交没有图片")
    submitted_ids = [int(item["file_id"]) for item in items]
    if set(submitted_ids) != set(records.keys()):
        raise AppError("排序请求必须包含当前提交的全部图片")
    for index, item in enumerate(items, start=1):
        record = records[int(item["file_id"])]
        record.sort_order = index
        record.page_no = index
        rotation = int(item.get("rotation", record.rotation) or 0)
        if rotation % 90 != 0:
            raise AppError("旋转角度必须是 90 的倍数")
        record.rotation = rotation % 360
    db.commit()
    return list_files(db, submission)


def resolve_readable_file(db: Session, user: User, file_id: int) -> SubmissionFile:
    """受控读取：学生仅本人，教师仅授权范围，管理员不限。"""
    record = db.get(SubmissionFile, file_id)
    if record is None:
        raise NotFoundError("文件不存在")
    submission = db.get(Submission, record.submission_id)
    if submission is None:
        raise NotFoundError("文件不存在")
    if user.role == UserRole.STUDENT:
        if submission.student_id != user.id:
            raise PermissionDeniedError("无权访问该文件")
        return record
    if user.role == UserRole.TEACHER:
        task = db.get(WritingTask, submission.task_id)
        if task is None or task.created_by != user.id:
            from app.services.access_service import assert_student_access

            assert_student_access(db, user, submission.student_id)
        return record
    if user.role == UserRole.ADMIN:
        return record
    raise PermissionDeniedError("无权访问该文件")


def read_file_path(record: SubmissionFile) -> Path:
    path = Path(record.stored_path).resolve()
    root = UPLOAD_DIR.resolve()
    if root not in path.parents:
        raise PermissionDeniedError("文件路径非法")
    if not path.exists():
        raise NotFoundError("文件已丢失")
    return path


def files_for_essay(db: Session, user: User, essay_id: int) -> list[SubmissionFile]:
    """按作文反查其提交来源的原始图片（用于「我的作文」查看图片原文）。"""
    from app.models.essay import Essay

    essay = db.get(Essay, essay_id)
    if essay is None:
        raise NotFoundError("作文不存在")
    if user.role == UserRole.STUDENT and essay.student_id != user.id:
        raise PermissionDeniedError("无权访问该作文")
    if user.role == UserRole.TEACHER:
        from app.services.access_service import assert_student_access

        assert_student_access(db, user, essay.student_id)
    answer = db.scalar(select(SubmissionAnswer).where(SubmissionAnswer.essay_id == essay_id))
    if answer is None:
        return []
    return list_files(db, db.get(Submission, answer.submission_id))


def upload_summary(db: Session, submission_id: int) -> dict:
    total = db.scalar(
        select(func.count(SubmissionFile.id)).where(SubmissionFile.submission_id == submission_id)
    ) or 0
    return {"submission_id": submission_id, "file_count": total}

def transcribe_submission(db: Session, student: User, submission_id: int) -> list[SubmissionFile]:
    """用视觉模型逐页识别图片文字，写入 extracted_text 与识别状态。

    不使用 OCR。识别结果仅作为「AI 识别文本」保存，需学生校对后才写入确认文本，
    未确认前不得进入评价队列。
    """
    from app.agents.llm_client import AgentLLMClient

    submission = _get_submission_for_write(db, student, submission_id)
    records = list_files(db, submission)
    if not records:
        raise AppError("尚未上传图片，无法识别")
    client = AgentLLMClient()
    submission.extraction_mode = "vision" if client.execution_mode == "remote" else "mock"
    submission.status = "processing"
    db.commit()

    failed: list[str] = []
    for record in records:
        record.extraction_status = "processing"
        db.commit()
        try:
            text, _usage = client.transcribe_image(record.stored_path, record.mime_type or "image/jpeg")
            record.extracted_text = text
            record.extraction_status = "done"
            record.error_message = None
        except AppError as exc:
            record.extraction_status = "failed"
            record.error_message = exc.message[:500]
            failed.append(f"第 {record.sort_order} 页：{exc.message}")
        db.commit()

    if failed and not any(item.extraction_status == "done" for item in records):
        submission.status = "uploaded"
        submission.extraction_note = "；".join(failed)[:1000]
        db.commit()
        raise AppError("全部图片识别失败：" + "；".join(failed)[:300])

    submission.status = "needs_confirmation"
    submission.extraction_note = "；".join(failed)[:1000] if failed else "识别完成，请校对文本后确认"
    db.commit()
    return list_files(db, submission)

def confirm_extraction(
    db: Session,
    student: User,
    submission_id: int,
    confirmed_texts: dict[int, str],
) -> Submission:
    """学生校对后确认识别文本。

    confirmed_texts 以 file_id 为键；未提交的文件沿用其识别文本。
    确认后写入 submission_answers.confirmed_text，并置提交为 ready，
    由 submit_image_submission 决定是否进入评价队列。
    """
    from app.models.submission import SubmissionAnswer
    from app.models.writing_task import TaskQuestion, WritingTask

    submission = _get_submission_for_write(db, student, submission_id)
    records = list_files(db, submission)
    if not records:
        raise AppError("尚未上传图片，无法确认")
    task = db.get(WritingTask, submission.task_id)
    questions = list(
        db.scalars(select(TaskQuestion).where(TaskQuestion.task_id == task.id).order_by(TaskQuestion.order_no)).all()
    )
    if not questions:
        raise AppError("该任务未配置子问题，无法确认作答")

    missing_pages = [
        item.sort_order for item in records if item.extraction_status != "done" and item.id not in confirmed_texts
    ]
    if missing_pages:
        raise AppError(f"以下页面尚未识别且未人工填写：{missing_pages}")

    merged_parts: list[str] = []
    for record in records:
        text = (confirmed_texts.get(record.id) or record.extracted_text or "").strip()
        if not text:
            raise AppError(f"第 {record.sort_order} 页确认为空，请填写或重新识别")
        merged_parts.append(text)
    merged = "\n\n".join(merged_parts)

    answer = db.scalar(
        select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id)
    )
    if answer is None:
        answer = SubmissionAnswer(
            submission_id=submission.id,
            question_id=questions[0].id,
            raw_text="\n\n".join((item.extracted_text or "") for item in records),
        )
        db.add(answer)
    answer.raw_text = "\n\n".join((item.extracted_text or "") for item in records)
    answer.confirmed_text = merged
    answer.char_count = len(merged)
    answer.is_confirmed = True
    submission.status = "ready"
    submission.confirmed_at = utc_now()
    submission.extraction_mode = submission.extraction_mode or "vision"
    db.commit()
    db.refresh(submission)
    return submission