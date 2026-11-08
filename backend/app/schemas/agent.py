"""专业 Agent 统一结构化输出：所有真实模型或 Mock 结果均须通过该校验。"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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