"""演示角色一键登录：三角色成功、关闭开关与密码不一致。"""
from app.core.config import settings


def test_demo_login_all_roles(client):
    for role in ("student", "teacher", "admin"):
        response = client.post("/api/v1/auth/demo-login", json={"role": role})
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["access_token"]
        assert data["user"]["role"] == role
        assert data["user"]["is_demo"] is True
        assert "password" not in str(data).lower()


def test_demo_status_exposes_accounts_without_password(client):
    response = client.get("/api/v1/auth/demo-status")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["enabled"] is True
    assert len(data["accounts"]) == 3
    assert all("password" not in str(item).lower() for item in data["accounts"])


def test_demo_login_disabled_returns_403(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_login_enabled", False)
    status = client.get("/api/v1/auth/demo-status")
    assert status.json()["data"]["enabled"] is False
    response = client.post("/api/v1/auth/demo-login", json={"role": "student"})
    assert response.status_code == 403
    assert "演示登录已关闭" in response.json()["message"]


def test_demo_login_password_mismatch_returns_401(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_password", "wrong-password-for-test")
    response = client.post("/api/v1/auth/demo-login", json={"role": "teacher"})
    assert response.status_code == 401
    assert "演示密码与账号不匹配" in response.json()["message"]