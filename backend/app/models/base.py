"""SQLAlchemy 声明式基类与公共字段。"""
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class UserRole:
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    ALL = (STUDENT, TEACHER, ADMIN)


class EssayStatus:
    DRAFT = "draft"
    SUBMITTED = "submitted"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Dimension:
    CONTENT = "content"
    ORGANIZATION = "organization"
    LANGUAGE = "language"
    ALL = (CONTENT, ORGANIZATION, LANGUAGE)