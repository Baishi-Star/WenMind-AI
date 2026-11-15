"""作文题目：首行标题确定性提取 + 标题匹配/复用 EssayPrompt。"""
from sqlalchemy import func, select

from app.models.essay import EssayPrompt
from app.services.ocr_service import extract_title_and_body
from tests.conftest import login_headers


def test_extract_title_and_body_removes_title_line():
    text = "邻里之间\n\n邻里之间，最珍贵的是互相体谅。\n\n例如，楼道里的灯坏了，邻居主动更换。"
    title, body = extract_title_and_body(text)
    assert title == "邻里之间"
    assert body.startswith("邻里之间，最珍贵的是互相体谅。")
    assert "楼道里的灯坏了" in body


def test_extract_rejects_first_line_ending_with_sentence_punctuation():
    text = "邻里之间，最珍贵的是互相体谅。\n\n例如，楼道里的灯坏了。"
    title, body = extract_title_and_body(text)
    assert title is None
    assert body == text


def test_extract_rejects_structure_marker():
    text = "一、开头\n正文内容。"
    assert extract_title_and_body(text)[0] is None


def test_extract_rejects_overlong_candidate():
    text = "这" * 41 + "\n正文内容。"
    assert extract_title_and_body(text)[0] is None


def test_extract_rejects_single_line_without_body():
    assert extract_title_and_body("邻里之间")[0] is None


def test_extract_strips_paired_decorations():
    text = "《邻里之间》\n正文内容。"
    title, body = extract_title_and_body(text)
    assert title == "邻里之间"
    assert body == "正文内容。"


def test_create_essay_stores_student_title_without_creating_prompt(client, db_session):
    headers = login_headers(client, "demo_student")
    payload = {
        "content": "这是用于验证学生标题落库的正文内容。",
        "submission_mode": "submit",
        "essay_title": "单元测试学生标题",
    }
    first = client.post("/api/v1/essays", json=payload, headers=headers)
    assert first.status_code == 201
    first_data = first.json()["data"]
    assert first_data["prompt_id"] is None
    assert first_data["essay_title"] == "单元测试学生标题"

    second = client.post("/api/v1/essays", json=payload, headers=headers)
    assert second.status_code == 201
    assert second.json()["data"]["prompt_id"] is None

    count = db_session.scalar(
        select(func.count(EssayPrompt.id)).where(EssayPrompt.title == "单元测试学生标题")
    )
    assert count == 0


def test_create_essay_without_title_is_free_essay(client):
    headers = login_headers(client, "demo_student")
    response = client.post(
        "/api/v1/essays",
        json={"content": "没有题目的自由作文正文。", "submission_mode": "submit"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["data"]["prompt_id"] is None


def test_prompt_id_takes_priority_over_essay_title(client, db_session):
    headers = login_headers(client, "demo_student")
    prompts = client.get("/api/v1/essays/prompts", headers=headers).json()["data"]
    prompt_id = prompts[0]["id"]
    response = client.post(
        "/api/v1/essays",
        json={
            "content": "同时提供 prompt_id 与标题时以 prompt_id 为准。",
            "submission_mode": "submit",
            "prompt_id": prompt_id,
            "essay_title": "不应被创建的标题",
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["data"]["prompt_id"] == prompt_id
    created = db_session.scalar(
        select(func.count(EssayPrompt.id)).where(EssayPrompt.title == "不应被创建的标题")
    )
    assert created == 0