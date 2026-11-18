"""提交状态在评价完成/失败后自动回写，并在读取入口自愈。"""
import app.api.submissions as submissions_api
from app.agents.llm_client import AgentLLMClient
from app.core.exceptions import AppError
from app.models.submission import Submission
from tests.conftest import login_headers


def _prepare_submission(client, monkeypatch):
    monkeypatch.setattr(submissions_api, "run_evaluation_task", lambda _evaluation_id: None)
    teacher = login_headers(client, "demo_teacher")
    student = login_headers(client, "demo_student")
    classes = client.get("/api/v1/classes", headers=teacher).json()["data"]
    rubrics = [
        item
        for item in client.get("/api/v1/teacher/rubric-versions", headers=teacher).json()["data"]
        if item["status"] == "published"
    ]
    assert classes and rubrics, "缺少班级或已发布量规"
    created = client.post(
        "/api/v1/teacher/tasks",
        json={
            "title": "提交状态回写验证",
            "prompt_text": "围绕城市绿地写一篇议论文，观点明确。",
            "requirements": "不少于 100 字",
            "rubric_version_id": rubrics[0]["id"],
            "targets": [{"target_type": "class", "target_id": classes[0]["id"]}],
        },
        headers=teacher,
    )
    assert created.status_code == 201, created.text
    task = created.json()["data"]
    published = client.post(f"/api/v1/teacher/tasks/{task['id']}/publish", headers=teacher)
    assert published.status_code == 200, published.text

    detail = client.get(f"/api/v1/student/tasks/{task['id']}", headers=student).json()["data"]
    question_id = detail["questions"][0]["id"]
    response = client.post(
        "/api/v1/student/submissions",
        json={
            "task_id": task["id"],
            "answers": [{"question_id": question_id, "content": "城市绿地让生活更美好，这是测试作文正文。"}],
        },
        headers=student,
    )
    assert response.status_code == 201, response.text
    return student, task, response.json()["data"]


def test_submission_becomes_evaluated_after_evaluation_completes(client, db_session, evaluation_runner, monkeypatch):
    student, task, submission = _prepare_submission(client, monkeypatch)
    evaluation_id = submission["answers"][0]["evaluation_id"]
    assert evaluation_id is not None

    evaluation_runner(evaluation_id)

    db_session.expire_all()
    stored = db_session.get(Submission, submission["id"])
    assert stored.status == "evaluated"
    fetched = client.get(f"/api/v1/student/submissions/{submission['id']}", headers=student).json()["data"]
    assert fetched["status"] == "evaluated"
    tasks = client.get("/api/v1/student/tasks", headers=student).json()["data"]
    item = next(entry for entry in tasks if entry["id"] == task["id"])
    assert item["submission_status"] == "evaluated"


def test_submission_becomes_failed_when_evaluation_fails(client, db_session, evaluation_runner, monkeypatch):
    _student, _task, submission = _prepare_submission(client, monkeypatch)
    evaluation_id = submission["answers"][0]["evaluation_id"]

    def boom(self, *args, **kwargs):
        raise AppError("模拟模型调用失败")

    monkeypatch.setattr(AgentLLMClient, "execute", boom)
    evaluation_runner(evaluation_id)

    db_session.expire_all()
    stored = db_session.get(Submission, submission["id"])
    assert stored.status == "failed"