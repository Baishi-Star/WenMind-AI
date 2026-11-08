"""知识库文档、检索请求与检索结果 Schema。"""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class KnowledgeDocumentResponse(BaseModel):
    id: int
    title: str
    source: str
    original_filename: str
    file_size: int
    status: str
    chunk_count: int
    embedding_mode: str | None
    embedding_model: str | None
    semantic: bool | None
    error_message: str | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10)
    evaluation_id: int | None = Field(default=None, gt=0)

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("检索问题至少需要 2 个字符")
        return value


class KnowledgeSearchResult(BaseModel):
    document_id: int
    document_name: str
    chunk_id: int
    content: str
    score: float
    metadata: dict


class KnowledgeSearchResponse(BaseModel):
    query: str
    top_k: int
    evaluation_id: int | None
    essay_id: int | None
    search_mode: str
    semantic: bool
    warning: str | None
    took_ms: float
    results: list[KnowledgeSearchResult]


class KnowledgeStatusResponse(BaseModel):
    indexed_chunks: int
    embedding_mode: str | None
    embedding_model: str | None
    semantic: bool | None
    index_persisted: bool
    remote_configured: bool
    upload_max_mb: int
    supported_extensions: list[str]