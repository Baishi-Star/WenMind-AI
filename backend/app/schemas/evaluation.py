"""评价任务响应模型；本阶段仅创建真实待处理任务，不生成虚构评分。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DimensionScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dimension: str
    original_score: float | None
    final_score: float | None
    max_score: float


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
    dimension_scores: list[DimensionScoreResponse] = Field(default_factory=list)