"""知识库业务服务：上传、解析、切片、索引、删除与 Top-K 检索。"""
import hashlib
import json
import threading
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import BASE_DIR, settings
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.evaluation import Evaluation
from app.models.knowledge import KbChunk, KbDocument
from app.models.user import User
from app.rag.chunker import chunk_blocks
from app.rag.embedding import create_embedding_adapter
from app.rag.parser import SUPPORTED_EXTENSIONS, parse_document
from app.rag.vector_store import FaissVectorStore
from app.schemas.knowledge import (
    KnowledgeDocumentResponse,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    KnowledgeStatusResponse,
)

logger = get_logger(__name__)
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
VECTOR_DIR = BASE_DIR / "data" / "vector_index"
vector_store = FaissVectorStore(VECTOR_DIR)
_mutation_lock = threading.RLock()


def _metadata(document: KbDocument) -> dict:
    try:
        return json.loads(document.metadata_json or "{}")
    except json.JSONDecodeError:
        return {}


def _chunk_metadata(chunk: KbChunk) -> dict:
    try:
        return json.loads(chunk.metadata_json or "{}")
    except json.JSONDecodeError:
        return {}


def serialize_document(db: Session, document: KbDocument) -> KnowledgeDocumentResponse:
    metadata = _metadata(document)
    chunk_count = db.scalar(select(func.count(KbChunk.id)).where(KbChunk.document_id == document.id)) or 0
    return KnowledgeDocumentResponse(
        id=document.id,
        title=document.title,
        source=document.source,
        original_filename=metadata.get("original_filename", ""),
        file_size=metadata.get("file_size", 0),
        status=document.status,
        chunk_count=chunk_count,
        embedding_mode=metadata.get("embedding_mode"),
        embedding_model=metadata.get("embedding_model"),
        semantic=metadata.get("semantic"),
        error_message=metadata.get("error_message"),
        is_demo=document.is_demo,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def list_documents(db: Session) -> list[KnowledgeDocumentResponse]:
    documents = db.scalars(select(KbDocument).order_by(KbDocument.created_at.desc(), KbDocument.id.desc())).all()
    return [serialize_document(db, document) for document in documents]


def _indexable_chunks(db: Session, include_document_id: int | None = None) -> list[KbChunk]:
    conditions = KbDocument.status == "ready"
    if include_document_id is not None:
        conditions = or_(conditions, KbDocument.id == include_document_id)
    statement = select(KbChunk).join(KbDocument, KbChunk.document_id == KbDocument.id).where(conditions).order_by(KbChunk.id)
    return list(db.scalars(statement).all())


def _mark_failed(db: Session, document_id: int, message: str) -> None:
    db.rollback()
    document = db.get(KbDocument, document_id)
    metadata = _metadata(document)
    metadata["error_message"] = message[:1000]
    document.metadata_json = json.dumps(metadata, ensure_ascii=False)
    document.status = "failed"
    db.commit()


def create_document(
    db: Session,
    user: User,
    filename: str,
    content: bytes,
    title: str | None,
    source: str,
) -> KnowledgeDocumentResponse:
    safe_filename = Path(filename or "").name
    suffix = Path(safe_filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise AppError("文件格式不支持，请上传 PDF、DOCX 或 TXT")
    max_bytes = settings.knowledge_upload_max_mb * 1024 * 1024
    if not content:
        raise AppError("不能上传空文件")
    if len(content) > max_bytes:
        raise AppError(f"文件不能超过 {settings.knowledge_upload_max_mb} MB")
    file_hash = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(KbDocument).where(KbDocument.file_hash == file_hash))
    if existing is not None:
        if existing.status != "failed":
            raise ConflictError("相同内容的文档已存在，请勿重复上传")
        db.execute(delete(KbChunk).where(KbChunk.document_id == existing.id))
        Path(existing.file_path).unlink(missing_ok=True)
        db.delete(existing)
        db.commit()

    with _mutation_lock:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stored_path = UPLOAD_DIR / f"{uuid4().hex}{suffix}"
        stored_path.write_bytes(content)
        document = KbDocument(
            title=(title or Path(safe_filename).stem).strip()[:200],
            source=source.strip()[:255] or "本地上传",
            file_path=str(stored_path),
            file_hash=file_hash,
            status="uploaded",
            metadata_json=json.dumps(
                {"original_filename": safe_filename, "file_size": len(content)}, ensure_ascii=False
            ),
            is_demo=user.is_demo,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        document.status = "processing"
        db.commit()
        try:
            blocks, parser_metadata = parse_document(stored_path)
            text_chunks = chunk_blocks(
                blocks,
                target_chars=settings.knowledge_chunk_target_chars,
                max_chars=settings.knowledge_chunk_max_chars,
            )
            if not text_chunks:
                raise AppError("文档中未解析到可用文本，请检查文件内容")
            for text_chunk in text_chunks:
                db.add(
                    KbChunk(
                        document_id=document.id,
                        chunk_text=text_chunk.content,
                        page_or_section=text_chunk.page_or_section[:100],
                        metadata_json=json.dumps(text_chunk.metadata, ensure_ascii=False),
                    )
                )
            db.flush()
            adapter = create_embedding_adapter()
            chunks = _indexable_chunks(db, include_document_id=document.id)
            index_metadata = vector_store.rebuild(chunks, adapter)
            for position, chunk in enumerate(chunks):
                chunk.vector_id = str(position)
            metadata = _metadata(document)
            metadata.update(parser_metadata)
            metadata.update(
                {
                    "embedding_mode": index_metadata["embedding_mode"],
                    "embedding_model": index_metadata["embedding_model"],
                    "semantic": index_metadata["semantic"],
                    "error_message": None,
                }
            )
            document.metadata_json = json.dumps(metadata, ensure_ascii=False)
            document.status = "ready"
            db.commit()
            logger.info("知识库文档索引完成 document_id=%s chunks=%s mode=%s", document.id, len(text_chunks), adapter.mode)
            return serialize_document(db, document)
        except AppError as exc:
            _mark_failed(db, document.id, exc.message)
            raise
        except Exception as exc:
            logger.exception("知识库文档处理失败 document_id=%s", document.id)
            _mark_failed(db, document.id, str(exc))
            raise AppError(f"文档解析或索引失败：{exc}") from exc


def delete_document(db: Session, document_id: int) -> dict:
    with _mutation_lock:
        document = db.get(KbDocument, document_id)
        if document is None:
            raise NotFoundError("知识库文档不存在")
        chunk_count = db.scalar(select(func.count(KbChunk.id)).where(KbChunk.document_id == document_id)) or 0
        stored_path = Path(document.file_path)
        db.execute(delete(KbChunk).where(KbChunk.document_id == document_id))
        db.delete(document)
        db.commit()
        vector_store.load()
        adapter = vector_store.current_adapter() or create_embedding_adapter()
        vector_store.rebuild(_indexable_chunks(db), adapter)
        stored_path.unlink(missing_ok=True)
        return {"deleted_document_id": document_id, "deleted_chunks": chunk_count}


def knowledge_status() -> KnowledgeStatusResponse:
    status = vector_store.status()
    return KnowledgeStatusResponse(
        **status,
        remote_configured=bool(settings.embedding_base_url and settings.embedding_api_key and settings.embedding_model),
        upload_max_mb=settings.knowledge_upload_max_mb,
        supported_extensions=sorted(SUPPORTED_EXTENSIONS),
    )


def search_knowledge(
    db: Session,
    query: str,
    top_k: int,
    evaluation_id: int | None = None,
) -> KnowledgeSearchResponse:
    started = time.perf_counter()
    essay_id = None
    if evaluation_id is not None:
        evaluation = db.get(Evaluation, evaluation_id)
        if evaluation is None:
            raise NotFoundError("关联评价任务不存在")
        essay_id = evaluation.essay_id
    hits = vector_store.search(query, top_k)
    status = vector_store.status()
    chunk_map = {}
    if hits:
        chunks = db.scalars(select(KbChunk).where(KbChunk.id.in_([chunk_id for chunk_id, _ in hits]))).all()
        chunk_map = {chunk.id: chunk for chunk in chunks}
    document_ids = {chunk.document_id for chunk in chunk_map.values()}
    documents = db.scalars(select(KbDocument).where(KbDocument.id.in_(document_ids))).all() if document_ids else []
    document_map = {document.id: document for document in documents}
    results = []
    for chunk_id, score in hits:
        chunk = chunk_map.get(chunk_id)
        if chunk is None:
            continue
        document = document_map[chunk.document_id]
        metadata = _chunk_metadata(chunk)
        metadata.update(
            {
                "page_or_section": chunk.page_or_section,
                "source": document.source,
                "vector_id": chunk.vector_id,
            }
        )
        results.append(
            KnowledgeSearchResult(
                document_id=document.id,
                document_name=document.title,
                chunk_id=chunk.id,
                content=chunk.chunk_text,
                score=round(score, 6),
                metadata=metadata,
            )
        )
    semantic = bool(status.get("semantic"))
    warning = None if semantic else "当前为 TF-IDF 词汇相似度检索（非语义 Embedding），不代表语义理解能力。"
    return KnowledgeSearchResponse(
        query=query,
        top_k=top_k,
        evaluation_id=evaluation_id,
        essay_id=essay_id,
        search_mode=status.get("embedding_mode") or "empty",
        semantic=semantic,
        warning=warning,
        took_ms=round((time.perf_counter() - started) * 1000, 2),
        results=results,
    )