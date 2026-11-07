"""注册、登录、密码哈希与当前用户接口测试。"""
from sqlalchemy import select

from app.models.user import User
from tests.conftest import login_headers


def test_demo_login_and_me(client):
    headers = login_headers(client, "demo_student")
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "demo_student"
    assert data["role"] == "student"
    assert data["is_demo"] is True
    assert "password" not in data
    assert "password_hash" not in data


def test_register_hashes_password_and_rejects_duplicate(client, db_session):
    payload = {"username": "new_student", "password": "SafePass@2026", "display_name": "新学生"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["data"]["role"] == "student"
    assert response.json()["data"]["is_demo"] is False

    user = db_session.scalar(select(User).where(User.username == "new_student"))
    assert user.password_hash != payload["password"]
    assert user.password_hash.startswith("pbkdf2_sha256$")

    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == 40900


def test_wrong_password_and_missing_token_are_rejected(client):
    wrong = client.post(
        "/api/v1/auth/login", json={"username": "demo_student", "password": "wrong-password"}
    )
    assert wrong.status_code == 401
    assert wrong.json()["code"] == 40100

    missing = client.get("/api/v1/auth/me")
    assert missing.status_code == 401
    assert missing.json()["code"] == 40100