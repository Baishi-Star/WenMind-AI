"""作文提交、上传文件与逐题作答模型。

提交统一归属于 writing_tasks：
- 文字/在线输入：submission_files 可为空，submission_answers 直接保存文本；
- 图片/扫描件/文档：文件保存到 submission_files，结构化文本再写入 submission_answers。
每个 answer 关联一条 essays 记录，从而复用现有 evaluations 多 Agent 评价链路。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SubmissionStatus:
    DRAFT = "draft"
    UPLOADED = "uploaded"
    NEEDS_CONFIRMATION = "needs_confirmation"
    READY = "ready"
    SUBMITTED = "submitted"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    FAILED = "failed"
    ALL = (DRAFT, UPLOADED, NEEDS_CONFIRMATION, READY, SUBMITTED, EVALUATING, EVALUATED, FAILED)


class FileKind:
    PHOTO = "photo"
    SCAN = "scan"
    DOCUMENT = "document"
    ALL = (PHOTO, SCAN, DOCUMENT)


class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("task_id", "student_id", "attempt_no", name="uq_submission_attempt"),
        Index("ix_submissions_student_status", "student_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("writing_tasks.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=SubmissionStatus.DRAFT, index=True)
    extraction_mode: Mapped[str | None] = mapped_column(String(32))
    extraction_note: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    files: Mapped[list["SubmissionFile"]] = relationship(back_populates="submission", cascade="all, delete-orphan")
    answers: Mapped[list["SubmissionAnswer"]] = relationship(back_populates="submission", cascade="all, delete-orphan")


class SubmissionFile(TimestampMixin, Base):
    __tablename__ = "submission_files"
    __table_args__ = (Index("ix_submission_files_submission_order", "submission_id", "sort_order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    file_kind: Mapped[str] = mapped_column(String(20), nullable=False, default=FileKind.PHOTO)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_no: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rotation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    extraction_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    extracted_text: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)

    submission: Mapped[Submission] = relationship(back_populates="files")


class SubmissionAnswer(TimestampMixin, Base):
    __tablename__ = "submission_answers"
    __table_args__ = (
        UniqueConstraint("submission_id", "question_id", name="uq_submission_answer_question"),
        Index("ix_submission_answers_essay", "essay_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("task_questions.id", ondelete="CASCADE"), nullable=False)
    essay_id: Mapped[int | None] = mapped_column(ForeignKey("essays.id", ondelete="SET NULL"))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confirmed_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_confidence: Mapped[float | None] = mapped_column(Float)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    submission: Mapped[Submission] = relationship(back_populates="answers")