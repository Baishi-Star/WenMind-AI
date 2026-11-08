"""知识库管理接口：仅管理员可上传、删除与执行管理端检索测试。"""
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.knowledge import (
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeStatusResponse,
)
from app.services.knowledge_service import (
    create_document,
    delete_document,
    knowledge_status,
    list_documents,
    search_knowledge,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
admin_only = require_roles(UserRole.ADMIN)


@router.get("/documents", response_model=ApiResponse[list[KnowledgeDocumentResponse]])
def get_documents(
    db: Session = Depends(get_db),
    _current_user: User = Depends(admin_only),
) -> ApiResponse[list[KnowledgeDocumentResponse]]:
    return success(list_documents(db))


@router.post("/upload", response_model=ApiResponse[KnowledgeDocumentResponse], status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    source: str = Form(default="本地上传"),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
) -> ApiResponse[KnowledgeDocumentResponse]:
    content = file.file.read(settings.knowledge_upload_max_mb * 1024 * 1024 + 1)
    document = create_document(db, current_user, file.filename or "", content, title, source)
    return success(document, message="文档解析、切片与索引已完成")


@router.delete("/documents/{document_id}", response_model=ApiResponse[dict])
def remove_document(
    document_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(admin_only),
) -> ApiResponse[dict]:
    return success(delete_document(db, document_id), message="文档及其切片、向量索引已删除")


@router.post("/search", response_model=ApiResponse[KnowledgeSearchResponse])
def search(
    payload: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(admin_only),
) -> ApiResponse[KnowledgeSearchResponse]:
    return success(search_knowledge(db, payload.query, payload.top_k, payload.evaluation_id))


@router.get("/status", response_model=ApiResponse[KnowledgeStatusResponse])
def get_status(
    _current_user: User = Depends(admin_only),
) -> ApiResponse[KnowledgeStatusResponse]:
    return success(knowledge_status())