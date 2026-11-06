"""业务异常与全局异常处理：对外返回可读信息，详细堆栈仅写入服务端日志。"""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.schemas.common import ApiResponse, ErrorCode

logger = get_logger(__name__)


class AppError(Exception):
    """业务异常基类，后续阶段直接抛出即可被统一处理。"""

    def __init__(
        self,
        message: str,
        code: int = ErrorCode.BAD_REQUEST,
        http_status: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(message, ErrorCode.NOT_FOUND, status.HTTP_404_NOT_FOUND)


class PermissionDeniedError(AppError):
    def __init__(self, message: str = "无权访问该资源") -> None:
        super().__init__(message, ErrorCode.FORBIDDEN, status.HTTP_403_FORBIDDEN)


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _build_response(request: Request, http_status: int, code: int, message: str) -> JSONResponse:
    payload = ApiResponse[None](code=code, message=message, data=None, request_id=_get_request_id(request))
    return JSONResponse(status_code=http_status, content=payload.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("业务异常 request_id=%s code=%s message=%s", _get_request_id(request), exc.code, exc.message)
        return _build_response(request, exc.http_status, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
            status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
            status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
            status.HTTP_405_METHOD_NOT_ALLOWED: ErrorCode.BAD_REQUEST,
        }
        code = code_map.get(exc.status_code, ErrorCode.BAD_REQUEST if exc.status_code < 500 else ErrorCode.INTERNAL_ERROR)
        message = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            message = "接口或资源不存在"
        return _build_response(request, exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(item) for item in error.get("loc", [])), "message": error.get("msg", "")}
            for error in exc.errors()
        ]
        logger.info("参数校验失败 request_id=%s details=%s", _get_request_id(request), details)
        first = details[0] if details else {"field": "", "message": "请求参数不合法"}
        message = f"参数校验失败：{first['field']} {first['message']}".strip()
        return _build_response(
            request, status.HTTP_422_UNPROCESSABLE_ENTITY, ErrorCode.VALIDATION_ERROR, message
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未处理异常 request_id=%s", _get_request_id(request), exc_info=exc)
        return _build_response(
            request, status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_ERROR, "服务器内部错误，请稍后重试"
        )