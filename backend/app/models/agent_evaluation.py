"""多 Agent 评价报告与 RAG 检索记录模型。"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utc_now


class EvaluationReport(TimestampMixin, Base):
    __tablename__ = "evaluation_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[int] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    execution_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    overall_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    quality_issues_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    training_suggestions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetrievalLog(TimestampMixin, Base):
    __tablename__ = "retrieval_logs"
    __table_args__ = (Index("ix_retrieval_logs_evaluation_created", "evaluation_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    search_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    semantic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    results_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")