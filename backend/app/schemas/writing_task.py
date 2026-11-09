"""写作任务与作文提交 Schema。"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskQuestionInput(BaseModel):
    label: str = Field(min_length=1, max_length=50)
    question_text: str = Field(min_length=1, max_length=4000)
    requirements: str = Field(default="", max_length=2000)
    answer_type: Literal["text", "image", "both"] = "text"
    max_score: float | None = Field(default=None, gt=0, le=200)


class TaskQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: int
    label: str
    question_text: str
    requirements: str
    answer_type: str
    max_score: float | None


class TaskTargetInput(BaseModel):
    target_type: Literal["class", "student"]
    target_id: int = Field(gt=0)


class TaskTargetResponse(BaseModel):
    id: int
    target_type: str
    target_id: int
    target_name: str


class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    prompt_text: str = Field(min_length=2, max_length=4000)
    requirements: str = Field(default="", max_length=4000)
    rubric_version_id: int | None = Field(default=None, gt=0)
    word_min: int = Field(default=0, ge=0, le=20000)
    word_max: int = Field(default=0, ge=0, le=20000)
    allow_resubmit: bool = False
    start_at: datetime | None = None
    due_at: datetime | None = None
    targets: list[TaskTargetInput] = Field(default_factory=list)
    questions: list[TaskQuestionInput] = Field(default_factory=list)

    @field_validator("questions")
    @classmethod
    def questions_unique_labels(cls, value):
        labels = [item.label.strip() for item in value]
        if len(labels) != len(set(labels)):
            raise ValueError("子问题标题不能重复")
        return value


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    prompt_text: str | None = Field(default=None, min_length=2, max_length=4000)
    requirements: str | None = Field(default=None, max_length=4000)
    rubric_version_id: int | None = Field(default=None, gt=0)
    word_min: int | None = Field(default=None, ge=0, le=20000)
    word_max: int | None = Field(default=None, ge=0, le=20000)
    allow_resubmit: bool | None = None
    start_at: datetime | None = None
    due_at: datetime | None = None
    targets: list[TaskTargetInput] | None = None
    questions: list[TaskQuestionInput] | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    source_type: str
    prompt_text: str
    requirements: str
    rubric_version_id: int | None
    word_min: int
    word_max: int
    allow_resubmit: bool
    status: str
    start_at: datetime | None
    due_at: datetime | None
    published_at: datetime | None
    is_demo: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    targets: list[TaskTargetResponse] = Field(default_factory=list)
    questions: list[TaskQuestionResponse] = Field(default_factory=list)
    target_class_names: list[str] = Field(default_factory=list)
    question_count: int = 0


class StudentTaskResponse(BaseModel):
    id: int
    title: str
    prompt_text: str
    requirements: str
    rubric_version_id: int | None
    word_min: int
    word_max: int
    allow_resubmit: bool
    status: str
    due_at: datetime | None
    teacher_name: str | None
    class_names: list[str] = Field(default_factory=list)
    questions: list[TaskQuestionResponse] = Field(default_factory=list)
    submission_status: str | None = None
    submission_id: int | None = None
    evaluation_statuses: list[dict] = Field(default_factory=list)
    is_overdue: bool = False


class AnswerInput(BaseModel):
    question_id: int = Field(gt=0)
    content: str = Field(min_length=1, max_length=20000)

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("作答内容不能为空")
        return stripped


class SubmissionCreate(BaseModel):
    task_id: int = Field(gt=0)
    answers: list[AnswerInput] = Field(min_length=1)


class SubmissionAnswerResponse(BaseModel):
    id: int
    question_id: int
    question_label: str
    essay_id: int | None
    evaluation_id: int | None
    evaluation_status: str | None
    confirmed_text: str
    char_count: int
    is_confirmed: bool


class SubmissionResponse(BaseModel):
    id: int
    task_id: int
    task_title: str
    student_id: int
    student_name: str
    attempt_no: int
    input_mode: str
    status: str
    extraction_mode: str | None
    extraction_note: str | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    answers: list[SubmissionAnswerResponse] = Field(default_factory=list)
    file_count: int = 0