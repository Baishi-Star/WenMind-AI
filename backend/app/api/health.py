"""健康检查接口：供前端连接测试与部署探活使用，无需鉴权。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.core.config import settings
from app.schemas.common import ApiResponse, success
from app.schemas.health import HealthData, LLMStatus

router = APIRouter(tags=["system"])


@router.get("/health", response_model=ApiResponse[HealthData], summary="服务健康检查")
async def health_check(request: Request) -> ApiResponse[HealthData]:
    started_at: datetime = request.app.state.started_at
    uptime = (datetime.now(timezone.utc) - started_at).total_seconds()
    data = HealthData(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        api_prefix=settings.api_v1_prefix,
        server_time=datetime.now(timezone.utc),
        uptime_seconds=round(uptime, 3),
        checks={"api": "ok"},
        llm=LLMStatus(
            mode=settings.llm_mode,
            configured=settings.llm_configured,
            model=settings.llm_model or "未配置",
        ),
    )
    return success(data, message="服务运行正常")