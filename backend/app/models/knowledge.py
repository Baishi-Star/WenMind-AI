"""知识库文档与文本切片模型。"""
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class KbDocument(TimestampMixin, Base):
    __tablename__ = "kb_documents"
    __table_args__ = (Index("ix_kb_documents_hash_status", "file_hash", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    chunks: Mapped[list["KbChunk"]] = relationship(back_populates="document")


class KbChunk(TimestampMixin, Base):
    __tablename__ = "kb_chunks"
    __table_args__ = (Index("ix_kb_chunks_document_vector", "document_id", "vector_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_or_section: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    vector_id: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    document: Mapped[KbDocument] = relationship(back_populates="chunks")