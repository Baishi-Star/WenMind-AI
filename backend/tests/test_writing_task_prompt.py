"""教师任务命题绑定 + 学生任务式提交（命题与标题分离）。"""
from sqlalchemy import select

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


def test_teacher_tasks_create_isolated_prompts(client, db_session):
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
    assert second.json()["data"]["prompt_id"] != first_prompt_id

    first_prompt = db_session.get(EssayPrompt, first_prompt_id)
    second_prompt = db_session.get(EssayPrompt, second.json()["data"]["prompt_id"])
    expected = f"材料：{prompt_text}\n写作要求：不少于 100 字"
    assert first_prompt.requirements == expected
    assert second_prompt.requirements == expected
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

def test_teacher_task_without_title_uses_prompt_summary(client):
    headers = login_headers(client, "demo_teacher")
    rubric_id = _published_rubric_id(client, headers)
    target = _class_target(client, headers)
    prompt_text = "任务标题留空时，应自动取作文题目材料的前六十字作为任务标题。"
    created = client.post(
        "/api/v1/teacher/tasks",
        json={
            "prompt_text": prompt_text,
            "requirements": "",
            "rubric_version_id": rubric_id,
            "targets": [target],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["data"]["title"] == prompt_text


def _create_published_task(client, headers, title, prompt_text, requirements):
    rubric_id = _published_rubric_id(client, headers)
    target = _class_target(client, headers)
    created = client.post(
        "/api/v1/teacher/tasks",
        json={
            "title": title,
            "prompt_text": prompt_text,
            "requirements": requirements,
            "rubric_version_id": rubric_id,
            "targets": [target],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    task = created.json()["data"]
    published = client.post(f"/api/v1/teacher/tasks/{task['id']}/publish", headers=headers)
    assert published.status_code == 200, published.text
    return task


def _submit_task(client, headers, task_id, content):
    detail = client.get(f"/api/v1/student/tasks/{task_id}", headers=headers).json()["data"]
    question_id = detail["questions"][0]["id"]
    response = client.post(
        "/api/v1/student/submissions",
        json={"task_id": task_id, "answers": [{"question_id": question_id, "content": content}]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_same_title_tasks_keep_own_material_in_evaluation_context(client, db_session, monkeypatch):
    import app.api.submissions as submissions_api

    monkeypatch.setattr(submissions_api, "run_evaluation_task", lambda _evaluation_id: None)
    teacher = login_headers(client, "demo_teacher")
    student = login_headers(client, "demo_student")
    first_task = _create_published_task(
        client, teacher, "同名任务", "材料甲：关于城市绿地的议论文材料。", "观点明确，不少于 400 字"
    )
    second_task = _create_published_task(
        client, teacher, "同名任务", "材料乙：关于校园阅读的议论文材料。", "结合材料，自选角度"
    )
    assert first_task["prompt_id"] != second_task["prompt_id"]

    from app.agents.llm_client import AgentLLMClient
    from app.agents.orchestrator import EvaluationOrchestrator
    from app.core.exceptions import AppError

    def run_and_capture(evaluation_id):
        captured = []

        def fake_execute(self, agent_name, task, essay_context, knowledge_context, previous_results):
            captured.append(essay_context)
            raise AppError("仅用于捕获评价上下文")

        monkeypatch.setattr(AgentLLMClient, "execute", fake_execute)
        EvaluationOrchestrator(db_session).run(evaluation_id)
        assert captured, "评价上下文未进入 Agent"
        return captured[0]

    first_submission = _submit_task(client, student, first_task["id"], "第一篇作文正文，围绕城市绿地展开。")
    first_context = run_and_capture(first_submission["answers"][0]["evaluation_id"])
    second_submission = _submit_task(client, student, second_task["id"], "第二篇作文正文，围绕校园阅读展开。")
    second_context = run_and_capture(second_submission["answers"][0]["evaluation_id"])

    assert "材料：材料甲：关于城市绿地的议论文材料。" in first_context["requirements"]
    assert "写作要求：观点明确，不少于 400 字" in first_context["requirements"]
    assert "材料乙" not in first_context["requirements"]
    assert "材料：材料乙：关于校园阅读的议论文材料。" in second_context["requirements"]
    assert "写作要求：结合材料，自选角度" in second_context["requirements"]
    assert "材料甲" not in second_context["requirements"]