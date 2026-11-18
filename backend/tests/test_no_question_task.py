"""无子问题任务的默认兜底与三子问题回归。"""
import base64

from sqlalchemy import func, select

from app.models.writing_task import TaskQuestion
from tests.conftest import login_headers


def _class_and_rubric(client, teacher):
    classes = client.get("/api/v1/classes", headers=teacher).json()["data"]
    rubrics = [item for item in client.get("/api/v1/teacher/rubric-versions", headers=teacher).json()["data"] if item["status"] == "published"]
    return classes[0]["id"], rubrics[0]["id"]


def test_task_without_questions_gets_default_and_accepts_submission(client, db_session):
    teacher = login_headers(client, "demo_teacher")
    class_id, rubric_id = _class_and_rubric(client, teacher)
    created = client.post(
        "/api/v1/teacher/tasks",
        json={
            "title": "无子问题任务",
            "prompt_text": "围绕邻里关系写一篇文章。",
            "requirements": "",
            "rubric_version_id": rubric_id,
            "targets": [{"target_type": "class", "target_id": class_id}],
        },
        headers=teacher,
    )
    assert created.status_code == 201, created.text
    task = created.json()["data"]
    assert len(task["questions"]) == 1
    assert task["questions"][0]["label"] == "作文"

    published = client.post(f"/api/v1/teacher/tasks/{task['id']}/publish", headers=teacher)
    assert published.status_code == 200, published.text

    student = login_headers(client, "demo_student")
    tasks = client.get("/api/v1/student/tasks", headers=student).json()["data"]
    item = next(entry for entry in tasks if entry["id"] == task["id"])
    assert len(item["questions"]) == 1
    question_id = item["questions"][0]["id"]

    submission = client.post(
        "/api/v1/student/submissions",
        json={
            "task_id": task["id"],
            "answers": [{"question_id": question_id, "content": "这是无子问题任务的正文。"}],
        },
        headers=student,
    )
    assert submission.status_code == 201, submission.text
    assert submission.json()["data"]["answers"][0]["essay_id"] is not None

    count = db_session.scalar(
        select(func.count(TaskQuestion.id)).where(TaskQuestion.task_id == task["id"])
    )
    assert count == 1


def test_task_with_multiple_questions_keeps_first_only(client):
    teacher = login_headers(client, "demo_teacher")
    class_id, rubric_id = _class_and_rubric(client, teacher)
    created = client.post(
        "/api/v1/teacher/tasks",
        json={
            "title": "多题目输入任务",
            "prompt_text": "围绕邻里关系分三点展开。",
            "requirements": "分点作答",
            "rubric_version_id": rubric_id,
            "targets": [{"target_type": "class", "target_id": class_id}],
            "questions": [
                {"label": "问题一", "question_text": "观点是什么？", "answer_type": "text"},
                {"label": "问题二", "question_text": "依据是什么？", "answer_type": "text"},
                {"label": "问题三", "question_text": "如何改进？", "answer_type": "text"},
            ],
        },
        headers=teacher,
    )
    assert created.status_code == 201, created.text
    questions = created.json()["data"]["questions"]
    assert len(questions) == 1
    assert questions[0]["label"] == "问题一"
    assert questions[0]["question_text"] == "观点是什么？"

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_task_without_questions_accepts_full_image_flow(client, db_session):
    teacher = login_headers(client, "demo_teacher")
    class_id, rubric_id = _class_and_rubric(client, teacher)
    created = client.post(
        "/api/v1/teacher/tasks",
        json={
            "title": "无子问题图片任务",
            "prompt_text": "无子问题任务的图片提交材料。",
            "requirements": "",
            "rubric_version_id": rubric_id,
            "targets": [{"target_type": "class", "target_id": class_id}],
        },
        headers=teacher,
    )
    assert created.status_code == 201, created.text
    task = created.json()["data"]
    assert len(task["questions"]) == 1
    published = client.post(f"/api/v1/teacher/tasks/{task['id']}/publish", headers=teacher)
    assert published.status_code == 200, published.text

    student = login_headers(client, "demo_student")
    image = client.post("/api/v1/student/submissions/image", json={"task_id": task["id"]}, headers=student)
    assert image.status_code == 201, image.text
    submission_id = image.json()["data"]["id"]

    upload = client.post(
        f"/api/v1/student/submissions/{submission_id}/files",
        headers=student,
        files={"files": ("page.png", PNG_1X1, "image/png")},
        data={"file_kind": "photo"},
    )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["data"][0]["id"]

    confirm = client.post(
        f"/api/v1/student/submissions/{submission_id}/confirm",
        headers=student,
        json={"pages": [{"file_id": file_id, "confirmed_text": "无子问题任务的图片正文。"}]},
    )
    assert confirm.status_code == 200, confirm.text

    submit = client.post(f"/api/v1/student/submissions/{submission_id}/submit", headers=student)
    assert submit.status_code == 200, submit.text
    assert submit.json()["data"]["answers"][0]["essay_id"] is not None

    count = db_session.scalar(
        select(func.count(TaskQuestion.id)).where(TaskQuestion.task_id == task["id"])
    )
    assert count == 1