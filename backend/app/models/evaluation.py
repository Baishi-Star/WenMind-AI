"""评价任务、维度评分、反馈证据与 Agent 运行记录模型。"""
from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, EvaluationStatus, TimestampMixin


class Evaluation(TimestampMixin, Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        Index("ix_evaluations_essay_status", "essay_id", "status"),
        Index("ix_evaluations_created_status", "created_at", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    essay_id: Mapped[int] = mapped_column(ForeignKey("essays.id", ondelete="CASCADE"), nullable=False)
    essay_version: Mapped[int] = mapped_column(Integer, nullable=False)
    rubric_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("rubric_versions.id", ondelete="SET NULL"), index=True
    )
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1.0")
    original_total_score: Mapped[float | None] = mapped_column(Float)
    final_total_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=EvaluationStatus.PENDING, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    essay: Mapped["Essay"] = relationship(back_populates="evaluations")
    dimension_scores: Mapped[list["DimensionScore"]] = relationship(back_populates="evaluation")
    feedback_items: Mapped[list["FeedbackItem"]] = relationship(back_populates="evaluation")


class DimensionScore(TimestampMixin, Base):
    __tablename__ = "dimension_scores"
    __table_args__ = (UniqueConstraint("evaluation_id", "dimension", name="uq_dimension_evaluation_dimension"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    original_score: Mapped[float | None] = mapped_column(Float)
    final_score: Mapped[float | None] = mapped_column(Float)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)

    evaluation: Mapped[Evaluation] = relationship(back_populates="dimension_scores")


class FeedbackItem(TimestampMixin, Base):
    __tablename__ = "feedback_items"
    __table_args__ = (Index("ix_feedback_evaluation_dimension", "evaluation_id", "dimension"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str | None] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    verified_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    evaluation: Mapped[Evaluation] = relationship(back_populates="feedback_items")


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_evaluation_agent", "evaluation_id", "agent_name"),
        Index("ix_agent_runs_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[int | None] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"))
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_usage_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)