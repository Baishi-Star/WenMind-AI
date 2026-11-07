"""评分量规版本与规则优化建议模型。"""
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RubricVersion(TimestampMixin, Base):
    __tablename__ = "rubric_versions"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_rubric_name_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    dimensions_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    change_reason: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class RuleProposal(TimestampMixin, Base):
    __tablename__ = "rule_proposals"
    __table_args__ = (Index("ix_rule_proposals_status_dimension", "status", "dimension"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    dimension: Mapped[str | None] = mapped_column(String(32))
    agent_name: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed")
    related_appeals_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))