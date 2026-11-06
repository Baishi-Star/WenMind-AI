"""请求级上下文：让统一响应体能自动携带 request_id，避免各路由重复传参。"""
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return request_id_var.get("")