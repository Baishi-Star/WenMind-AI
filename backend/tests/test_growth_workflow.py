"""成长画像、教师复核口径、训练任务与班级分析测试。"""
from sqlalchemy import func, select

from app.models.growth import GrowthProfile, GrowthSnapshot, TrainingTask, TrainingTaskDetail
from tests.conftest import create_completed_evaluation, login_headers

CONTENT_TEMPLATE = (
    "成长来自对同一问题的持续修改。{marker}\n\n"
    "例如，我会先核对原文证据，再判断建议是否符合自己的表达意图。\n\n"
    "因此，我保留个性表达，同时补充论据解释和段落衔接。"
)


def _review_first_evaluation(client, student_headers, teacher_headers, detail):
    feedback = next(item for item in detail["feedback_items"] if any(e["verified_status"] == "verified" for e in item["evidence"]))
    evidence = next(item for item in feedback["evidence"] if item["verified_status"] == "verified")
    appeal = client.post(
        "/api/v1/appeals",
        json={
            "evaluation_id": detail["id"],
            "feedback_item_id": feedback["id"],
            "reason_type": "creative_expression_misjudged",
            "dimension": feedback["dimension"] if feedback["dimension"] in {"content", "organization", "language", "overall", "topic"} else "overall",
            "description": "教师复核该表述是否被误判，并保留本人表达意图。",
            "evidence": evidence,
        },
        headers=student_headers,
    )
    assert appeal.status_code == 201
    reviewed = client.post(
        f"/api/v1/teacher/appeals/{appeal.json()['data']['id']}/review",
        json={
            "decision": "adjust",
            "change_reason": "教师确认该表达属于有意设计，调整最终诊断值。",
            "dimension_updates": [
                {"dimension": "content", "final_score": 5},
                {"dimension": "organization", "final_score": 4},
                {"dimension": "language", "final_score": 4},
            ],
            "feedback_changes": [],
            "added_feedback": [],
            "classification_codes": ["expression_misjudgment"],
            "classification_note": "表达被误判",
            "revised_summary": "保留个性表达，调整诊断。",
        },
        headers=teacher_headers,
    )
    assert reviewed.status_code == 200


def test_growth_uses_teacher_final_and_generates_training(client, db_session, evaluation_runner):
    student_headers = login_headers(client, "demo_student")
    teacher_headers = login_headers(client, "demo_teacher")
    details = []
    for index in range(1, 4):
        _, detail = create_completed_evaluation(
            client, student_headers, evaluation_runner, CONTENT_TEMPLATE.format(marker=f"第{index}次")
        )
        details.append(detail)
    _review_first_evaluation(client, student_headers, teacher_headers, details[0])

    profile_response = client.get("/api/v1/growth/profile", headers=student_headers)
    assert profile_response.status_code == 200, profile_response.text
    profile = profile_response.json()["data"]
    assert profile["sample_count"] == 3
    assert profile["reviewed_count"] == 1
    assert profile["unreviewed_count"] == 2
    assert profile["insufficient_data"] is False
    assert len(profile["capabilities"]) == 5
    unavailable = {item["key"] for item in profile["capabilities"] if not item["available"]}
    assert unavailable == {"topic", "argumentation"}
    assert profile["capabilities"][0]["score"] is not None

    history = client.get("/api/v1/growth/history", headers=student_headers).json()["data"]
    assert len(history["points"]) == 3
    assert history["points"][0]["review_status"] == "teacher_confirmed"
    assert all(point["review_status"] == "ai_unreviewed" for point in history["points"][1:])

    tasks_response = client.get("/api/v1/training/tasks", headers=student_headers)
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()["data"]["tasks"]
    assert tasks
    assert tasks[0]["objective"] and tasks[0]["reason"] and tasks[0]["content"]

    completed = client.post(
        f"/api/v1/training/tasks/{tasks[0]['id']}/complete",
        json={"result_text": "完成了论据解释链训练，并记录了下次修改方向。"},
        headers=student_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["data"]["status"] == "completed"
    assert completed.json()["data"]["result_text"]

    refreshed = client.get("/api/v1/growth/profile", headers=student_headers).json()["data"]
    assert refreshed["training_completed"] >= 1
    assert db_session.scalar(select(func.count(GrowthProfile.id))) == 1
    assert db_session.scalar(select(func.count(GrowthSnapshot.id))) >= 3
    assert db_session.scalar(select(func.count(TrainingTask.id))) >= 1
    assert db_session.scalar(select(func.count(TrainingTaskDetail.id))) >= 1

    class_analytics = client.get("/api/v1/teacher/classes/1/analytics", headers=teacher_headers)
    assert class_analytics.status_code == 200
    class_data = class_analytics.json()["data"]
    assert class_data["student_count"] == 3
    assert class_data["evaluation_count"] == 3
    assert class_data["students"]
    assert class_data["teaching_suggestions"]

    teacher_view = client.get("/api/v1/growth/profile?student_id=1", headers=teacher_headers)
    assert teacher_view.status_code == 200
    assert teacher_view.json()["data"]["student_id"] == 1

    other_student_headers = login_headers(client, "demo_student2")
    forbidden = client.get("/api/v1/growth/profile?student_id=1", headers=other_student_headers)
    assert forbidden.status_code == 403


def test_insufficient_samples_are_marked_data_accumulating(client):
    headers = login_headers(client, "demo_student3")
    profile = client.get("/api/v1/growth/profile", headers=headers).json()["data"]
    assert profile["sample_count"] == 0
    assert profile["insufficient_data"] is True
    assert profile["trend_status"] == "no_data"
    assert "暂无" in profile["notice"]
    assert len(profile["capabilities"]) == 5
    assert {item["key"] for item in profile["capabilities"] if not item["supported"]} == {"topic", "argumentation"}
    scored_dimensions = {item["key"] for item in profile["capabilities"] if item["supported"]}
    assert scored_dimensions == {"content", "organization", "language"}
    assert all(not item["available"] for item in profile["capabilities"] if item["supported"])
    history = client.get("/api/v1/growth/history", headers=headers).json()["data"]
    assert history["points"] == []
    assert history["insufficient_data"] is True