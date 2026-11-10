"""作文图片标注 Schema：坐标为归一化 0~1。"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AnnotationResponse(BaseModel):
    id: int
    essay_id: int
    submission_file_id: int | None
    source: str
    label: str
    shape: str
    x: float
    y: float
    width: float
    height: float
    page_no: int | None
    note: str | None
    color: str
    feedback_item_id: int | None
    created_at: datetime


class AnnotationCreate(BaseModel):
    submission_file_id: int | None = Field(default=None, gt=0)
    label: Literal["evidence", "problem", "strength", "teacher_note", "correction"] = "teacher_note"
    shape: Literal["rect", "point"] = "rect"
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(default=0, ge=0, le=1)
    height: float = Field(default=0, ge=0, le=1)
    page_no: int | None = Field(default=None, ge=1)
    note: str | None = Field(default=None, max_length=2000)
    color: str = Field(default="#f59e0b", max_length=24)

    @model_validator(mode="after")
    def ensure_within_bounds(self):
        if self.x + self.width > 1.0001 or self.y + self.height > 1.0001:
            raise ValueError("标注坐标超出图片范围（必须为归一化 0~1 且不越界）")
        if self.shape == "rect" and (self.width <= 0 or self.height <= 0):
            raise ValueError("矩形标注必须指定正的宽度与高度")
        return self