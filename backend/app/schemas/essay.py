"""作文题目、草稿、提交与响应模型。"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class EssayCreate(BaseModel):
    prompt_id: int | None = None
    content: str
    submission_mode: Literal["draft", "submit"] = "submit"
    source_type: Literal["text", "image"] = "text"
    image_path: str | None = None
    ocr_text: str | None = None

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("作文正文不能为空")
        return stripped


class EssayImageUploadResponse(BaseModel):
    image_token: str
    preview_url: str
    size_bytes: int
    ocr_enabled: bool


class EssayOcrRequest(BaseModel):
    image_token: str


class EssayOcrResponse(BaseModel):
    status: str
    text: str
    message: str


class EssayOcrStatusResponse(BaseModel):
    enabled: bool


class EssayUpdate(BaseModel):
    prompt_id: int | None = None
    content: str
    submission_mode: Literal["draft", "submit"] = "draft"

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("作文正文不能为空")
        return stripped


class EssayPromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    requirements: str
    rubric_version_id: int | None
    is_demo: bool


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
    source_type: str = "text"
    image_path: str | None = None
    ocr_status: str = "none"
    created_at: datetime
    updated_at: datetime


class EssayDetail(EssayListItem):
    content: str