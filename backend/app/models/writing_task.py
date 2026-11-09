"""写作任务、下发范围与子问题模型。

两种作文题目来源统一抽象为 writing_tasks：
- source_type=teacher：教师布置任务，可定向到班级或学生；
- source_type=student_self：学生自主提交时自动创建的个人任务，范围仅本人。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TaskStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"
    ALL = (DRAFT, PUBLISHED, CLOSED, ARCHIVED)


class TaskSource:
    TEACHER = "teacher"
    STUDENT_SELF = "student_self"
    ALL = (TEACHER, STUDENT_SELF)


class TargetType:
    CLASS = "class"
    STUDENT = "student"
    ALL = (CLASS, STUDENT)


class WritingTask(TimestampMixin, Base):
    __tablename__ = "writing_tasks"
    __table_args__ = (Index("ix_writing_tasks_status_due", "status", "due_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default=TaskSource.TEACHER, index=True)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rubric_version_id: Mapped[int | None] = mapped_column(ForeignKey("rubric_versions.id", ondelete="SET NULL"))
    word_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    word_max: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    allow_resubmit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TaskStatus.DRAFT, index=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    targets: Mapped[list["TaskTarget"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    questions: Mapped[list["TaskQuestion"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskTarget(TimestampMixin, Base):
    __tablename__ = "task_targets"
    __table_args__ = (
        UniqueConstraint("task_id", "target_type", "target_id", name="uq_task_target"),
        Index("ix_task_targets_target", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("writing_tasks.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)

    task: Mapped[WritingTask] = relationship(back_populates="targets")


class TaskQuestion(TimestampMixin, Base):
    __tablename__ = "task_questions"
    __table_args__ = (UniqueConstraint("task_id", "order_no", name="uq_task_question_order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("writing_tasks.id", ondelete="CASCADE"), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answer_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    max_score: Mapped[float | None] = mapped_column(Float)

    task: Mapped[WritingTask] = relationship(back_populates="questions")