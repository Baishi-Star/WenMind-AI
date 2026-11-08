"""规则建议详情与量规版本治理记录。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RuleProposalDetail(TimestampMixin, Base):
    __tablename__ = "rule_proposal_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[int] = mapped_column(
        ForeignKey("rule_proposals.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    source_tag: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    current_rule: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_effect: Mapped[str] = mapped_column(Text, nullable=False, default="")
    typical_cases_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decision_note: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RubricVersionGovernance(TimestampMixin, Base):
    __tablename__ = "rubric_version_governance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rubric_version_id: Mapped[int] = mapped_column(
        ForeignKey("rubric_versions.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    proposal_id: Mapped[int | None] = mapped_column(ForeignKey("rule_proposals.id", ondelete="SET NULL"))
    parent_version_id: Mapped[int | None] = mapped_column(ForeignKey("rubric_versions.id", ondelete="SET NULL"))
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    regression_result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    published_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))