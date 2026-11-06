"""阶段 1 接口测试：统一响应结构、健康检查、404 异常处理、request_id 透传。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    # 使用上下文管理器，确保 lifespan 启动逻辑被执行
    with TestClient(app) as test_client:
        yield test_client


def test_health_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["message"] == "服务运行正常"
    data = body["data"]
    assert data["status"] == "ok"
    assert data["checks"]["api"] == "ok"
    assert data["api_prefix"] == "/api/v1"
    assert data["llm"]["mode"] in {"mock", "remote"}
    assert data["uptime_seconds"] >= 0
    # 健康检查不得泄露密钥字段
    assert "api_key" not in str(data).lower()


def test_root_returns_service_info(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["health"] == "/api/v1/health"


def test_unknown_route_uses_unified_error_structure(client):
    response = client.get("/api/v1/not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == 40400
    assert body["data"] is None
    assert body["message"]


def test_response_contains_request_id(client):
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request-001"})
    assert response.headers["X-Request-ID"] == "test-request-001"
    assert response.json()["request_id"] == "test-request-001"


def test_health_generates_request_id_when_absent(client):
    response = client.get("/api/v1/health")
    body = response.json()
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]