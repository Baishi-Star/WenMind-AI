"""作文图片标注模型：AI 证据框与教师批注，坐标为归一化 0~1。"""
from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AnnotationSource:
    AI = "ai"
    TEACHER = "teacher"
    ALL = (AI, TEACHER)


class AnnotationShape:
    RECT = "rect"
    POINT = "point"
    ALL = (RECT, POINT)


class EssayAnnotation(TimestampMixin, Base):
    __tablename__ = "essay_annotations"
    __table_args__ = (
        Index("ix_essay_annotations_essay_file", "essay_id", "submission_file_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    essay_id: Mapped[int] = mapped_column(ForeignKey("essays.id", ondelete="CASCADE"), nullable=False)
    submission_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("submission_files.id", ondelete="CASCADE")
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default=AnnotationSource.AI)
    label: Mapped[str] = mapped_column(String(64), nullable=False, default="evidence")
    shape: Mapped[str] = mapped_column(String(16), nullable=False, default=AnnotationShape.RECT)
    # 归一化坐标（0~1），避免缩放下错位
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    width: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    page_no: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(24), nullable=False, default="#6366f1")
    feedback_item_id: Mapped[int | None] = mapped_column(ForeignKey("feedback_items.id", ondelete="SET NULL"))
    review_id: Mapped[int | None] = mapped_column(ForeignKey("review_records.id", ondelete="SET NULL"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    is_readonly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)