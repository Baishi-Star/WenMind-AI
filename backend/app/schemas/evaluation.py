"""评价任务、Agent 运行、RAG 记录与综合报告响应模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.interaction import FeedbackItemResponse


class DimensionScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dimension: str
    original_score: float | None
    final_score: float | None
    max_score: float


class AgentRunResponse(BaseModel):
    id: int
    agent_name: str
    model_name: str
    prompt_version: str
    status: str
    latency_ms: int
    input_summary: dict
    output: dict | None
    token_usage: dict | None
    error_message: str | None
    created_at: datetime


class RetrievalLogResponse(BaseModel):
    id: int
    query: str
    search_mode: str
    semantic: bool
    results: list[dict]
    created_at: datetime


class EvaluationReportResponse(BaseModel):
    execution_mode: str
    overall_summary: str
    quality_status: str
    quality_issues: list[str]
    training_suggestions: list[str]
    report: dict
    started_at: datetime
    completed_at: datetime | None


class EvaluationResponse(BaseModel):
    id: int
    essay_id: int
    essay_version: int
    rubric_version_id: int | None
    prompt_version: str
    original_total_score: float | None
    final_total_score: float | None
    status: str
    error_message: str | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    diagnostic_notice: str = "AI 评价属于教学诊断性参考，不等同于正式考试评分。"
    dimension_scores: list[DimensionScoreResponse] = Field(default_factory=list)
    report: EvaluationReportResponse | None = None
    agent_runs: list[AgentRunResponse] = Field(default_factory=list)
    retrievals: list[RetrievalLogResponse] = Field(default_factory=list)
    feedback_items: list[FeedbackItemResponse] = Field(default_factory=list)