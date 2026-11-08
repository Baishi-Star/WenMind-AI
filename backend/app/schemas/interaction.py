"""学生反馈、追问与申诉请求响应模型。"""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.agent import EvidenceItem


class FeedbackItemResponse(BaseModel):
    id: int
    dimension: str
    category: str
    content: str
    suggestion: str | None
    evidence: list[EvidenceItem]
    verified_status: str
    created_at: datetime


class QuestionCreate(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    feedback_item_id: int | None = Field(default=None, gt=0)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("追问内容不能为空")
        return value


class QuestionResponse(BaseModel):
    id: int
    evaluation_id: int
    feedback_item_id: int | None
    question: str
    answer: str
    evidence: list[EvidenceItem]
    suggestions: list[str]
    status: str
    execution_mode: str
    model_name: str
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class AppealCreate(BaseModel):
    evaluation_id: int = Field(gt=0)
    feedback_item_id: int | None = Field(default=None, gt=0)
    reason_type: str = Field(min_length=2, max_length=64)
    dimension: str = Field(min_length=2, max_length=32)
    description: str = Field(min_length=5, max_length=2000)
    evidence: EvidenceItem | None = None


class AppealItemResponse(BaseModel):
    id: int
    feedback_item_id: int | None
    student_note: str
    evidence: list[EvidenceItem]


class AppealResponse(BaseModel):
    id: int
    evaluation_id: int
    essay_id: int
    student_id: int
    reason_type: str
    dimension: str
    description: str
    status: str
    submitted_at: datetime
    items: list[AppealItemResponse]
    review_records: list[dict]