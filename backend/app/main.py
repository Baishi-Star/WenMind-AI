"""WenMind AI 后端应用入口。

启动方式（在 backend 目录下）：
    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import register_middlewares
from app.db.init_db import init_database
from app.db.seed import seed_demo_data
from app.db.session import SessionLocal
from app.schemas.common import ApiResponse, success

setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started_at = datetime.now(timezone.utc)
    if settings.auto_init_db:
        init_database()
        if settings.auto_seed_demo:
            with SessionLocal() as db:
                seed_demo_data(db)
    logger.info(
        "%s v%s 启动，环境=%s，API 前缀=%s，LLM 模式=%s",
        settings.app_name,
        settings.app_version,
        settings.app_env,
        settings.api_v1_prefix,
        settings.llm_mode,
    )
    yield
    logger.info("应用关闭")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="WenMind AI（文思智评）——高中生个性化写作成长系统后端服务",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
# 模块级兜底：测试客户端等不触发 lifespan 的场景也能读取启动时间
app.state.started_at = datetime.now(timezone.utc)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_middlewares(app)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", response_model=ApiResponse[dict], tags=["system"], summary="服务信息")
async def root() -> ApiResponse[dict]:
    return success(
        {
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        },
        message="WenMind AI 后端服务已启动",
    )