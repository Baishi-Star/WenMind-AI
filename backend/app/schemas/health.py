"""健康检查响应数据模型。"""
from datetime import datetime

from pydantic import BaseModel


class LLMStatus(BaseModel):
    mode: str
    configured: bool
    model: str


class HealthData(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    api_prefix: str
    server_time: datetime
    uptime_seconds: float
    checks: dict[str, str]
    llm: LLMStatus