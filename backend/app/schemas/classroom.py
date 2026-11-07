"""班级请求与响应模型。"""
from datetime import datetime

from pydantic import BaseModel, Field


class ClassCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    teacher_id: int | None = None


class ClassResponse(BaseModel):
    id: int
    name: str
    teacher_id: int
    teacher_name: str
    student_count: int
    is_demo: bool
    created_at: datetime