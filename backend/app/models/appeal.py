"""学生申诉与教师复核记录模型：复核永不覆盖 AI 原始评价。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utc_now


class Appeal(TimestampMixin, Base):
    __tablename__ = "appeals"
    __table_args__ = (
        Index("ix_appeals_student_status", "student_id", "status"),
        Index("ix_appeals_evaluation_status", "evaluation_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason_type: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    items: Mapped[list["AppealItem"]] = relationship(back_populates="appeal")
    review_records: Mapped[list["ReviewRecord"]] = relationship(back_populates="appeal")


class ReviewRecord(TimestampMixin, Base):
    __tablename__ = "review_records"
    __table_args__ = (Index("ix_review_records_reviewer_time", "reviewer_id", "reviewed_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id", ondelete="CASCADE"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    original_score_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    revised_score_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    review_comment: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    appeal: Mapped[Appeal] = relationship(back_populates="review_records")