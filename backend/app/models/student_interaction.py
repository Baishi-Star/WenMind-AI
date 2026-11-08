"""学生评价追问与申诉关联项模型。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EvaluationQuestion(TimestampMixin, Base):
    __tablename__ = "evaluation_questions"
    __table_args__ = (Index("ix_questions_evaluation_student", "evaluation_id", "student_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    feedback_item_id: Mapped[int | None] = mapped_column(ForeignKey("feedback_items.id", ondelete="SET NULL"))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    suggestions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")
    execution_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AppealItem(TimestampMixin, Base):
    __tablename__ = "appeal_items"
    __table_args__ = (Index("ix_appeal_items_appeal_feedback", "appeal_id", "feedback_item_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id", ondelete="CASCADE"), nullable=False)
    feedback_item_id: Mapped[int | None] = mapped_column(ForeignKey("feedback_items.id", ondelete="SET NULL"))
    student_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_location_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    appeal: Mapped["Appeal"] = relationship(back_populates="items")