"""作文请求与响应模型。"""
from datetime import datetime

from pydantic import BaseModel, field_validator


class EssayCreate(BaseModel):
    prompt_id: int | None = None
    content: str

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("作文正文不能为空")
        return stripped


class EssayListItem(BaseModel):
    id: int
    student_id: int
    student_name: str
    prompt_id: int | None
    prompt_title: str | None
    content_version: int
    char_count: int
    status: str
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class EssayDetail(EssayListItem):
    content: str