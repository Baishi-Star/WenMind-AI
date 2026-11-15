"""请求级中间件：注入 request_id 并记录访问日志，便于串联一次完整调用。"""
import time
from uuid import uuid4

from fastapi import FastAPI, Request

from app.core.context import request_id_var
from app.core.logging import get_logger

logger = get_logger("wenmind.access")


def register_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex[:16]
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "%s %s status=%s cost=%sms request_id=%s",
                request.method,
                request.url.path,
                status_code,
                elapsed_ms,
                request_id,
            )
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response