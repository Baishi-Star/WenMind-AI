"""作文题目与作文正文模型。"""
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, EssayStatus, TimestampMixin


class EssayPrompt(TimestampMixin, Base):
    __tablename__ = "essay_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    requirements: Mapped[str] = mapped_column(Text, nullable=False)
    rubric_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("rubric_versions.id", ondelete="SET NULL"), index=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    essays: Mapped[list["Essay"]] = relationship(back_populates="prompt")


class Essay(TimestampMixin, Base):
    __tablename__ = "essays"
    __table_args__ = (
        Index("ix_essays_student_created", "student_id", "created_at"),
        Index("ix_essays_prompt_status", "prompt_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prompt_id: Mapped[int | None] = mapped_column(ForeignKey("essay_prompts.id", ondelete="SET NULL"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=EssayStatus.SUBMITTED, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    image_path: Mapped[str | None] = mapped_column(String(500))
    ocr_status: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    ocr_text: Mapped[str | None] = mapped_column(Text)

    prompt: Mapped[EssayPrompt | None] = relationship(back_populates="essays")
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="essay")