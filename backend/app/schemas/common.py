"""统一 API 响应结构与业务错误码。

响应格式：
{
  "code": 0,
  "message": "success",
  "data": {...},
  "request_id": "...",
  "timestamp": "..."
}
"""
from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.context import get_request_id

T = TypeVar("T")


class ErrorCode:
    SUCCESS = 0
    BAD_REQUEST = 40000
    VALIDATION_ERROR = 42200
    UNAUTHORIZED = 40100
    FORBIDDEN = 40300
    NOT_FOUND = 40400
    CONFLICT = 40900
    INTERNAL_ERROR = 50000
    UPSTREAM_UNAVAILABLE = 50300


class ApiResponse(BaseModel, Generic[T]):
    code: int = ErrorCode.SUCCESS
    message: str = "success"
    data: T | None = None
    request_id: str = Field(default_factory=get_request_id)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def success(data: T | None = None, message: str = "success") -> ApiResponse[T]:
    return ApiResponse[T](data=data, message=message)