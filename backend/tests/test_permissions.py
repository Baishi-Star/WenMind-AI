"""角色与资源归属权限测试。"""
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models.base import UserRole
from app.models.essay import Essay
from app.models.user import User
from tests.conftest import login_headers


def test_student_cannot_create_class_but_teacher_can(client):
    student_headers = login_headers(client, "demo_student")
    forbidden = client.post("/api/v1/classes", json={"name": "越权班级"}, headers=student_headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == 40300

    teacher_headers = login_headers(client, "demo_teacher")
    created = client.post("/api/v1/classes", json={"name": "高一（2）班"}, headers=teacher_headers)
    assert created.status_code == 201
    assert created.json()["data"]["student_count"] == 0


def test_student_cannot_read_other_students_essay(client, db_session):
    other_essay = db_session.scalar(select(Essay).join(User, Essay.student_id == User.id).where(User.username == "demo_student2"))
    student_headers = login_headers(client, "demo_student")
    forbidden = client.get(f"/api/v1/essays/{other_essay.id}", headers=student_headers)
    assert forbidden.status_code == 403

    teacher_headers = login_headers(client, "demo_teacher")
    allowed = client.get(f"/api/v1/essays/{other_essay.id}", headers=teacher_headers)
    assert allowed.status_code == 200
    assert allowed.json()["data"]["id"] == other_essay.id


def test_teacher_cannot_read_essay_outside_assigned_classes(client, db_session):
    other_teacher = User(
        username="other_teacher",
        password_hash=hash_password("OtherPass@2026"),
        display_name="其他教师",
        role=UserRole.TEACHER,
    )
    db_session.add(other_teacher)
    db_session.commit()
    token, _ = create_access_token(other_teacher.id, other_teacher.role)
    essay = db_session.scalar(select(Essay).limit(1))
    response = client.get(f"/api/v1/essays/{essay.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_class_visibility_follows_role(client):
    student_headers = login_headers(client, "demo_student")
    student_classes = client.get("/api/v1/classes", headers=student_headers)
    assert student_classes.status_code == 200
    assert len(student_classes.json()["data"]) == 1
    assert student_classes.json()["data"][0]["student_count"] == 3

    admin_headers = login_headers(client, "demo_admin")
    admin_classes = client.get("/api/v1/classes", headers=admin_headers)
    assert admin_classes.status_code == 200
    assert len(admin_classes.json()["data"]) == 1