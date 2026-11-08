"""专业 Agent 统一结构化输出：所有真实模型或 Mock 结果均须通过该校验。"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _as_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "、".join(_as_text(item) for item in value)
    if isinstance(value, dict):
        return "；".join(f"{key}: {_as_text(item)}" for key, item in value.items() if item not in (None, "", []))
    return str(value)


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    quote: str = ""
    start_char: int | None = None
    end_char: int | None = None
    reason: str = ""
    suggestion: str = ""
    verified_status: Literal["pending", "verified", "unverified"] = "pending"
    match_type: str | None = None


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    agent_name: str
    task: str
    analysis: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)
    status: Literal["completed", "failed"] = "completed"
    dimension: str | None = None
    diagnostic_score: int | None = Field(default=None, ge=1, le=5)
    grade: str | None = None
    strengths: list[str] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)
    knowledge_refs: list[str] = Field(default_factory=list)
    overall_summary: str | None = None
    training_suggestions: list[str] = Field(default_factory=list)
    quality_status: Literal["passed", "needs_review", "failed"] | None = None
    quality_issues: list[str] = Field(default_factory=list)

    @field_validator("diagnostic_score", mode="before")
    @classmethod
    def normalize_diagnostic_score(cls, value, info):
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value) if value.is_integer() else None
        if isinstance(value, str):
            stripped = value.strip()
            return int(stripped) if stripped.isdigit() else None
        if isinstance(value, dict):
            expected_dimension = {
                "content_agent": "content",
                "structure_agent": "organization",
                "language_agent": "language",
            }.get(info.data.get("agent_name"))
            if expected_dimension is None:
                return None
            candidate = value.get(expected_dimension)
            if isinstance(candidate, bool):
                return None
            if isinstance(candidate, (int, float)) and float(candidate).is_integer():
                return int(candidate)
        return None

    @field_validator("suggestions", "strengths", "problems", "knowledge_refs", "training_suggestions", "quality_issues", mode="before")
    @classmethod
    def normalize_text_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if not isinstance(value, list):
            return [_as_text(value)]
        return [_as_text(item) for item in value if item not in (None, "", [])]


class AgentRunRecord(BaseModel):
    agent_name: str
    model_name: str
    prompt_version: str
    input_summary: dict
    output: AgentResult | None
    status: str
    latency_ms: int
    token_usage: dict | None
    error_message: str | None