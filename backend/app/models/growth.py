"""学生成长画像、历史快照与训练任务模型。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class GrowthProfile(TimestampMixin, Base):
    __tablename__ = "growth_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class GrowthSnapshot(TimestampMixin, Base):
    __tablename__ = "growth_snapshots"
    __table_args__ = (Index("ix_growth_snapshots_student_created", "student_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    evaluation_id: Mapped[int | None] = mapped_column(ForeignKey("evaluations.id", ondelete="SET NULL"))
    dimension_scores_json: Mapped[str] = mapped_column(Text, nullable=False)


class TrainingTask(TimestampMixin, Base):
    __tablename__ = "training_tasks"
    __table_args__ = (Index("ix_training_tasks_student_status", "student_id", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))