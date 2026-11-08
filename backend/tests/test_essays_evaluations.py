"""作文持久化、评价任务状态与演示数据测试。"""
from sqlalchemy import func, select

from app.models.essay import Essay, EssayPrompt
from app.models.evaluation import Evaluation
from app.models.user import User
from tests.conftest import login_headers


def test_demo_seed_counts_and_flags(db_session):
    assert db_session.scalar(select(func.count(User.id))) == 5
    assert db_session.scalar(select(func.count(EssayPrompt.id))) == 3
    assert db_session.scalar(select(func.count(Essay.id))) == 3
    assert db_session.scalar(select(func.count(Evaluation.id))) == 0
    assert all(user.is_demo for user in db_session.scalars(select(User)).all())


def test_student_can_create_and_list_only_own_essays(client):
    headers = login_headers(client, "demo_student")
    initial = client.get("/api/v1/essays", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["data"]["total"] == 1

    created = client.post(
        "/api/v1/essays",
        json={"prompt_id": 1, "content": "这是一篇用于验证数据库持久化的学生作文正文。"},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["data"]["char_count"] > 0
    assert created.json()["data"]["content_version"] == 1

    updated = client.get("/api/v1/essays", headers=headers)
    assert updated.json()["data"]["total"] == 2
    assert all(item["student_name"] == "演示学生一" for item in updated.json()["data"]["items"])


def test_blank_essay_and_teacher_submission_are_rejected(client):
    student_headers = login_headers(client, "demo_student")
    blank = client.post("/api/v1/essays", json={"content": "   "}, headers=student_headers)
    assert blank.status_code == 422
    assert blank.json()["code"] == 42200

    teacher_headers = login_headers(client, "demo_teacher")
    forbidden = client.post("/api/v1/essays", json={"content": "教师不应代学生提交"}, headers=teacher_headers)
    assert forbidden.status_code == 403


def test_evaluation_is_created_as_pending_without_fake_scores(client, db_session):
    essay = db_session.scalar(select(Essay).join(User, Essay.student_id == User.id).where(User.username == "demo_student"))
    headers = login_headers(client, "demo_student")
    created = client.post(f"/api/v1/evaluations/{essay.id}", headers=headers)
    assert created.status_code == 201
    data = created.json()["data"]
    assert data["status"] == "pending"
    assert data["original_total_score"] is None
    assert data["final_total_score"] is None
    assert data["rubric_version_id"] is not None
    assert data["prompt_version"] == "agent-prompt-v1.0"

    detail = client.get(f"/api/v1/evaluations/{data['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["essay_version"] == 1

    duplicate = client.post(f"/api/v1/evaluations/{essay.id}", headers=headers)
    assert duplicate.status_code == 409

    other_headers = login_headers(client, "demo_student2")
    forbidden = client.get(f"/api/v1/evaluations/{data['id']}", headers=other_headers)
    assert forbidden.status_code == 403