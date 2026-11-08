"""成长画像、趋势、训练任务与班级分析 Schema。"""
from datetime import datetime

from pydantic import BaseModel, Field


class CapabilityItem(BaseModel):
    key: str
    label: str
    supported: bool
    available: bool
    score: float | None = None
    sample_count: int = 0
    source: str
    note: str


class GrowthPoint(BaseModel):
    evaluation_id: int
    essay_id: int
    essay_title: str
    created_at: datetime
    rubric_version_id: int | None
    review_status: str
    review_decision: str | None
    reviewed_at: datetime | None
    scores: dict[str, float]
    unweighted_average: float | None


class GrowthProfileResponse(BaseModel):
    student_id: int
    student_name: str
    sample_count: int
    reviewed_count: int
    unreviewed_count: int
    insufficient_data: bool
    trend_status: str
    notice: str
    version_mixed: bool
    rubric_versions: list[int]
    capabilities: list[CapabilityItem]
    averages: dict[str, float]
    strengths: list[str]
    weaknesses: list[str]
    training_pending: int
    training_completed: int
    latest_evaluation_at: datetime | None


class GrowthHistoryResponse(BaseModel):
    student_id: int
    points: list[GrowthPoint]
    insufficient_data: bool
    notice: str
    rubric_versions: list[int]


class TrainingTaskResponse(BaseModel):
    id: int
    task_type: str
    ability: str
    objective: str
    reason: str
    content: str
    status: str
    source_evaluation_ids: list[int]
    result_text: str | None
    created_at: datetime
    completed_at: datetime | None


class TrainingTaskListResponse(BaseModel):
    tasks: list[TrainingTaskResponse]
    pending_count: int
    completed_count: int
    notice: str


class TrainingCompleteRequest(BaseModel):
    result_text: str = Field(min_length=2, max_length=2000)


class StudentAnalyticsSummary(BaseModel):
    student_id: int
    student_name: str
    sample_count: int
    reviewed_count: int
    averages: dict[str, float]
    weakest_dimension: str | None
    needs_data: bool


class ClassAnalyticsResponse(BaseModel):
    class_id: int
    class_name: str
    student_count: int
    essay_count: int
    evaluation_count: int
    reviewed_evaluation_count: int
    insufficient_data: bool
    notice: str
    dimension_averages: dict[str, float]
    dimension_distribution: dict[str, dict[str, int]]
    dimension_weak_ratios: dict[str, float]
    students: list[StudentAnalyticsSummary]
    top_confirmed_issues: list[dict]
    feedback_problem_counts: dict[str, int]
    appeal_status_counts: dict[str, int]
    teaching_suggestions: list[dict]
    rubric_versions: list[int]