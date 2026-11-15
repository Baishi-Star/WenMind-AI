"""教师任务命题绑定 + 学生任务式提交（命题与标题分离）。"""
from sqlalchemy import func, select

from app.models.essay import EssayPrompt
from app.models.writing_task import WritingTask
from tests.conftest import login_headers


def _published_rubric_id(client, teacher_headers):
    rubrics = client.get("/api/v1/teacher/rubric-versions", headers=teacher_headers).json()["data"]
    published = [item for item in rubrics if item["status"] == "published"]
    assert published, "缺少已发布量规"
    return published[0]["id"]


def _class_target(client, teacher_headers):
    classes = client.get("/api/v1/classes", headers=teacher_headers).json()["data"]
    assert classes, "缺少班级"
    return {"target_type": "class", "target_id": classes[0]["id"]}


def test_teacher_task_creates_and_reuses_prompt(client, db_session):
    headers = login_headers(client, "demo_teacher")
    rubric_id = _published_rubric_id(client, headers)
    target = _class_target(client, headers)
    prompt_text = "同一份作文材料：围绕邻里关系写一篇议论文，观点明确。"
    base = {
        "prompt_text": prompt_text,
        "requirements": "不少于 100 字",
        "rubric_version_id": rubric_id,
        "targets": [target],
    }
    first = client.post("/api/v1/teacher/tasks", json={**base, "title": "任务甲"}, headers=headers)
    assert first.status_code == 201, first.text
    first_prompt_id = first.json()["data"]["prompt_id"]
    assert first_prompt_id is not None

    second = client.post("/api/v1/teacher/tasks", json={**base, "title": "任务乙"}, headers=headers)
    assert second.status_code == 201, second.text
    assert second.json()["data"]["prompt_id"] == first_prompt_id

    count = db_session.scalar(
        select(func.count(EssayPrompt.id)).where(EssayPrompt.title == prompt_text[:60])
    )
    assert count == 1
    task = db_session.scalar(select(WritingTask).where(WritingTask.title == "任务甲"))
    assert task.prompt_id == first_prompt_id


def test_student_task_submission_binds_prompt_and_student_title(client, db_session):
    teacher_headers = login_headers(client, "demo_teacher")
    rubric_id = _published_rubric_id(client, teacher_headers)
    target = _class_target(client, teacher_headers)
    prompt_text = "任务式提交流程验证材料：邻里关系议论文。"
    created = client.post(
        "/api/v1/teacher/tasks",
        json={
            "title": "任务式提交流程验证",
            "prompt_text": prompt_text,
            "requirements": "观点明确",
            "rubric_version_id": rubric_id,
            "targets": [target],
        },
        headers=teacher_headers,
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["data"]["id"]
    task_prompt_id = created.json()["data"]["prompt_id"]
    published = client.post(f"/api/v1/teacher/tasks/{task_id}/publish", headers=teacher_headers)
    assert published.status_code == 200, published.text

    student_headers = login_headers(client, "demo_student")
    essay = client.post(
        "/api/v1/essays",
        json={
            "content": "这是学生校对后的作文正文，不含标题行。",
            "submission_mode": "submit",
            "task_id": task_id,
            "essay_title": "学生自拟标题",
        },
        headers=student_headers,
    )
    assert essay.status_code == 201, essay.text
    data = essay.json()["data"]
    assert data["prompt_id"] == task_prompt_id
    assert data["essay_title"] == "学生自拟标题"