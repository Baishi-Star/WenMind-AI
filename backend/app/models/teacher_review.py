"""教师复核叠加记录：原始 AI 评价永不修改，教师结果独立保存。"""
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class FeedbackReviewChange(TimestampMixin, Base):
    __tablename__ = "feedback_review_changes"
    __table_args__ = (Index("ix_feedback_changes_evaluation_item", "evaluation_id", "feedback_item_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    feedback_item_id: Mapped[int] = mapped_column(ForeignKey("feedback_items.id", ondelete="CASCADE"), nullable=False)
    review_id: Mapped[int | None] = mapped_column(ForeignKey("review_records.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    revised_content: Mapped[str | None] = mapped_column(Text)
    revised_suggestion: Mapped[str | None] = mapped_column(Text)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)


class TeacherFeedbackItem(TimestampMixin, Base):
    __tablename__ = "teacher_feedback_items"
    __table_args__ = (Index("ix_teacher_feedback_evaluation", "evaluation_id", "dimension"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    review_id: Mapped[int | None] = mapped_column(ForeignKey("review_records.id", ondelete="SET NULL"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="teacher_added")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str | None] = mapped_column(Text)


class ReviewIssueTag(TimestampMixin, Base):
    __tablename__ = "review_issue_tags"
    __table_args__ = (Index("ix_review_issue_tags_tag_appeal", "tag_code", "appeal_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id", ondelete="CASCADE"), nullable=False)
    review_id: Mapped[int | None] = mapped_column(ForeignKey("review_records.id", ondelete="SET NULL"))
    tag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    confirmed_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)