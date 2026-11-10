"""作文提交文件接口：图片上传、页序管理、受控读取。"""
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.writing_task import ExtractionConfirmRequest, FileReorderItem, SubmissionFileResponse
from app.services import file_service

router = APIRouter(tags=["submission-files"])
student_only = require_roles(UserRole.STUDENT)


def _serialize(record) -> SubmissionFileResponse:
    return SubmissionFileResponse(
        id=record.id,
        submission_id=record.submission_id,
        file_kind=record.file_kind,
        original_filename=record.original_filename,
        mime_type=record.mime_type,
        file_size=record.file_size,
        page_no=record.page_no,
        sort_order=record.sort_order,
        rotation=record.rotation,
        width=record.width,
        height=record.height,
        extraction_status=record.extraction_status,
        extracted_text=record.extracted_text,
        error_message=record.error_message,
        created_at=record.created_at,
    )


@router.post(
    "/student/submissions/{submission_id}/files",
    response_model=ApiResponse[list[SubmissionFileResponse]],
    status_code=status.HTTP_201_CREATED,
)
def upload_submission_files(
    submission_id: int,
    files: list[UploadFile] = File(...),
    file_kind: str = Form(default="photo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[list[SubmissionFileResponse]]:
    uploads = [(item.filename or "image", item.file.read()) for item in files]
    created = file_service.upload_images(db, current_user, submission_id, uploads, file_kind)
    return success([_serialize(item) for item in created], message=f"已上传 {len(created)} 张图片")


@router.get("/student/submissions/{submission_id}/files", response_model=ApiResponse[list[SubmissionFileResponse]])
def list_submission_files(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[SubmissionFileResponse]]:
    from app.services.submission_service import get_submission_detail
    from app.models.submission import Submission

    submission = db.get(Submission, submission_id)
    if submission is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("提交记录不存在")
    get_submission_detail(db, current_user, submission_id)
    return success([_serialize(item) for item in file_service.list_files(db, submission)])


@router.delete("/student/submissions/{submission_id}/files/{file_id}", response_model=ApiResponse[dict])
def delete_submission_file(
    submission_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[dict]:
    return success(file_service.delete_file(db, current_user, submission_id, file_id), message="图片已删除")


@router.put("/student/submissions/{submission_id}/files/order", response_model=ApiResponse[list[SubmissionFileResponse]])
def reorder_submission_files(
    submission_id: int,
    items: list[FileReorderItem],
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[list[SubmissionFileResponse]]:
    records = file_service.reorder_files(
        db, current_user, submission_id, [item.model_dump() for item in items]
    )
    return success([_serialize(item) for item in records], message="页序与旋转已更新")


@router.post("/student/submissions/{submission_id}/transcribe", response_model=ApiResponse[list[SubmissionFileResponse]])
def transcribe_submission_files(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[list[SubmissionFileResponse]]:
    records = file_service.transcribe_submission(db, current_user, submission_id)
    return success(
        [_serialize(item) for item in records],
        message="图片识别完成，请校对文本后确认；确认前不会进入评价队列",
    )


@router.post("/student/submissions/{submission_id}/confirm", response_model=ApiResponse[dict])
def confirm_submission_extraction(
    submission_id: int,
    payload: ExtractionConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[dict]:
    confirmed = {item.file_id: item.confirmed_text for item in payload.pages}
    submission = file_service.confirm_extraction(db, current_user, submission_id, confirmed)
    return success(
        {"submission_id": submission.id, "status": submission.status},
        message="识别文本已确认，可进入评价队列",
    )


@router.get("/essays/{essay_id}/files", response_model=ApiResponse[list[SubmissionFileResponse]])
def list_essay_files(
    essay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[SubmissionFileResponse]]:
    records = file_service.files_for_essay(db, current_user, essay_id)
    return success([_serialize(item) for item in records])


@router.get("/files/{file_id}")
def read_submission_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    record = file_service.resolve_readable_file(db, current_user, file_id)
    path = file_service.read_file_path(record)
    return FileResponse(path, media_type=record.mime_type or "application/octet-stream", filename=record.original_filename)