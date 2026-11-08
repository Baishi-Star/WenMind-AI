"""教师申诉复核、争议统计与规则治理 Schema。"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.agent import EvidenceItem
from app.schemas.evaluation import EvaluationResponse


class TeacherAppealListItem(BaseModel):
    id: int
    evaluation_id: int
    essay_id: int
    student_id: int
    student_name: str
    class_names: list[str]
    essay_title: str
    reason_type: str
    dimension: str
    description: str
    status: str
    submitted_at: datetime
    reviewed_at: datetime | None
    decision: str | None


class ClassificationSuggestion(BaseModel):
    tag_code: str
    label: str
    rationale: str
    source: str = "rule_based_assist"


class TeacherFeedbackView(BaseModel):
    id: int
    dimension: str
    category: str
    content: str
    suggestion: str | None
    evidence: list[EvidenceItem]
    verified_status: str
    review_action: str = "kept"
    teacher_content: str | None = None
    teacher_suggestion: str | None = None
    teacher_feedback: bool = False


class TeacherAppealDetail(BaseModel):
    id: int
    evaluation_id: int
    essay_id: int
    student_id: int
    student_name: str
    class_names: list[str]
    essay_title: str
    essay_content: str
    reason_type: str
    dimension: str
    description: str
    status: str
    submitted_at: datetime
    appeal_items: list[dict]
    evaluation: EvaluationResponse
    feedback_items: list[TeacherFeedbackView]
    teacher_feedback_items: list[dict]
    review_records: list[dict]
    confirmed_tags: list[str]
    classification_suggestions: list[ClassificationSuggestion]


class DimensionUpdate(BaseModel):
    dimension: Literal["content", "organization", "language"]
    final_score: int = Field(ge=1, le=5)


class FeedbackChange(BaseModel):
    feedback_item_id: int = Field(gt=0)
    action: Literal["kept", "modified", "deleted"]
    content: str | None = Field(default=None, max_length=2000)
    suggestion: str | None = Field(default=None, max_length=2000)

    @field_validator("content")
    @classmethod
    def modified_content_required(cls, value, info):
        if info.data.get("action") == "modified" and not value:
            raise ValueError("修改反馈时必须填写新内容")
        return value


class AddedFeedback(BaseModel):
    dimension: Literal["content", "organization", "language", "overall", "topic"]
    content: str = Field(min_length=2, max_length=2000)
    suggestion: str | None = Field(default=None, max_length=2000)


class TeacherReviewRequest(BaseModel):
    decision: Literal["uphold", "adjust", "need_more_info"]
    change_reason: str = Field(min_length=5, max_length=2000)
    dimension_updates: list[DimensionUpdate] = Field(default_factory=list)
    feedback_changes: list[FeedbackChange] = Field(default_factory=list)
    added_feedback: list[AddedFeedback] = Field(default_factory=list)
    classification_codes: list[str] = Field(min_length=1, max_length=6)
    classification_note: str | None = Field(default=None, max_length=1000)
    revised_summary: str | None = Field(default=None, max_length=2000)


class TeacherReviewResponse(BaseModel):
    review_id: int
    appeal_id: int
    appeal_status: str
    decision: str
    reviewed_at: datetime
    final_dimension_scores: list[dict]
    confirmed_tags: list[str]


class AppealPatternStats(BaseModel):
    days: int
    sample_count: int
    reviewed_count: int
    small_sample_warning: bool
    status_counts: dict[str, int]
    reason_counts: dict[str, int]
    dimension_counts: dict[str, int]
    tag_counts: list[dict]
    agent_counts: list[dict]
    rubric_version_counts: list[dict]
    generated_rule_proposal_ids: list[int] = Field(default_factory=list)


class RuleProposalListItem(BaseModel):
    id: int
    title: str
    source_tag: str
    dimension: str | None
    agent_name: str | None
    problem_description: str
    current_rule: str
    typical_cases: list[dict]
    suggestion: str
    expected_effect: str
    status: str
    related_appeal_ids: list[int]
    created_at: datetime
    approver_id: int | None
    decided_at: datetime | None
    decision_note: str | None
    result_version_id: int | None = None


class RuleProposalDecision(BaseModel):
    decision_note: str = Field(min_length=2, max_length=2000)
    title: str | None = Field(default=None, max_length=200)
    problem_description: str | None = Field(default=None, max_length=4000)
    suggestion: str | None = Field(default=None, max_length=4000)
    expected_effect: str | None = Field(default=None, max_length=2000)
    rule_content: str = Field(min_length=2, max_length=4000)
    change_reason: str = Field(min_length=5, max_length=2000)


class RuleProposalReject(BaseModel):
    decision_note: str = Field(min_length=2, max_length=2000)


class RubricVersionView(BaseModel):
    id: int
    name: str
    version: str
    status: str
    change_reason: str | None
    created_by: int | None
    created_at: datetime
    approver_id: int | None
    approved_at: datetime | None
    effective_at: datetime | None
    parent_version_id: int | None
    proposal_id: int | None
    regression_result: dict


class RegressionResponse(BaseModel):
    rubric_version_id: int
    status: str
    sample_count: int
    checks: list[dict]
    mode: str
    message: str