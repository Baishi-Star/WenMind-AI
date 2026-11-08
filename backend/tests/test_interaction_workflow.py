"""学生作文、评价证据、追问、申诉与教师越权测试。"""
from sqlalchemy import func, select

from app.core.security import create_access_token, hash_password
from app.models.appeal import Appeal, ReviewRecord
from app.models.base import UserRole
from app.models.essay import Essay
from app.models.evaluation import DimensionScore, FeedbackItem
from app.models.student_interaction import EvaluationQuestion
from app.models.teacher_review import FeedbackReviewChange, ReviewIssueTag, TeacherFeedbackItem
from app.models.user import User
from tests.conftest import create_completed_evaluation, login_headers

ESSAY_CONTENT = (
    "评价不只是给结果，更要说明判断依据。写作时，我先记录观点，再寻找能够支撑观点的事实和经历。\n\n"
    "例如，一次班级讨论中，同学追问我的依据，我才发现原来的论据没有解释清楚。于是我补充材料，并说明材料与观点之间的关系。\n\n"
    "因此，面对评价，我会先核对原文证据，再提出追问或申诉。评价、修改与复核应当形成连续过程。"
)


def _feedback_with_evidence(detail):
    return next(item for item in detail["feedback_items"] if any(e["verified_status"] == "verified" for e in item["evidence"]))


def _appeal_payload(detail, feedback):
    evidence = next(item for item in feedback["evidence"] if item["verified_status"] == "verified")
    return {
        "evaluation_id": detail["id"],
        "feedback_item_id": feedback["id"],
        "reason_type": "creative_expression_misjudged",
        "dimension": feedback["dimension"] if feedback["dimension"] in {"content", "organization", "language", "overall", "topic"} else "overall",
        "description": "这句话是我有意的表达，希望教师结合上下文复核，而不是按固定句式直接判错。",
        "evidence": evidence,
    }


def test_draft_submit_evaluation_and_verified_evidence(client, db_session, evaluation_runner):
    headers = login_headers(client, "demo_student")
    draft_response = client.post(
        "/api/v1/essays",
        json={"prompt_id": 1, "content": ESSAY_CONTENT, "submission_mode": "draft"},
        headers=headers,
    )
    assert draft_response.status_code == 201
    essay = draft_response.json()["data"]
    assert essay["status"] == "draft"

    submitted = client.put(
        f"/api/v1/essays/{essay['id']}",
        json={"prompt_id": 1, "content": ESSAY_CONTENT + "\n\n我会继续保留自己的表达风格。", "submission_mode": "submit"},
        headers=headers,
    )
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "submitted"
    assert submitted.json()["data"]["content_version"] == 2

    evaluation_response = client.post(f"/api/v1/evaluations/{essay['id']}", headers=headers)
    assert evaluation_response.status_code == 201
    evaluation_id = evaluation_response.json()["data"]["id"]
    evaluation_runner(evaluation_id)
    detail = client.get(f"/api/v1/evaluations/{evaluation_id}", headers=headers).json()["data"]

    assert detail["status"] == "completed"
    assert len(detail["agent_runs"]) == 6
    assert detail["report"]["execution_mode"] == "mock"
    assert detail["original_total_score"] is None
    assert detail["final_total_score"] is None
    assert len(detail["feedback_items"]) > 0
    assert detail["retrievals"][0]["search_mode"] == "local_tfidf"

    essay_detail = client.get(f"/api/v1/essays/{essay['id']}", headers=headers).json()["data"]
    verified = [
        evidence
        for item in detail["feedback_items"]
        for evidence in item["evidence"]
        if evidence["verified_status"] == "verified"
    ]
    assert verified
    for evidence in verified:
        assert essay_detail["content"][evidence["start_char"] : evidence["end_char"]] == evidence["quote"]

    persisted = db_session.get(Essay, essay["id"])
    assert persisted.status == "completed"
    assert db_session.scalar(select(func.count(FeedbackItem.id)).where(FeedbackItem.evaluation_id == evaluation_id)) > 0


def test_multi_turn_questions_are_persisted_with_context(client, db_session, evaluation_runner):
    headers = login_headers(client, "demo_student")
    _, detail = create_completed_evaluation(client, headers, evaluation_runner, ESSAY_CONTENT)
    feedback = _feedback_with_evidence(detail)

    first = client.post(
        f"/api/v1/evaluations/{detail['id']}/questions",
        json={"feedback_item_id": feedback["id"], "question": "为什么这一项得分较低？"},
        headers=headers,
    )
    assert first.status_code == 201
    assert first.json()["data"]["status"] == "completed"
    assert first.json()["data"]["execution_mode"] == "mock"
    assert first.json()["data"]["answer"]

    second = client.post(
        f"/api/v1/evaluations/{detail['id']}/questions",
        json={"feedback_item_id": feedback["id"], "question": "如果保留我的表达风格，应该如何修改？"},
        headers=headers,
    )
    assert second.status_code == 201
    assert "表达" in second.json()["data"]["answer"]

    history = client.get(f"/api/v1/evaluations/{detail['id']}/questions", headers=headers)
    assert history.status_code == 200
    assert len(history.json()["data"]) == 2
    assert db_session.scalar(select(func.count(EvaluationQuestion.id))) == 2

    other_headers = login_headers(client, "demo_student2")
    forbidden = client.post(
        f"/api/v1/evaluations/{detail['id']}/questions",
        json={"question": "越权尝试"},
        headers=other_headers,
    )
    assert forbidden.status_code == 403


def test_appeal_teacher_review_preserves_ai_original_and_blocks_cross_class(client, db_session, evaluation_runner):
    student_headers = login_headers(client, "demo_student")
    _, detail = create_completed_evaluation(client, student_headers, evaluation_runner, ESSAY_CONTENT)
    feedback = _feedback_with_evidence(detail)
    original_feedback = db_session.get(FeedbackItem, feedback["id"]).content

    created = client.post("/api/v1/appeals", json=_appeal_payload(detail, feedback), headers=student_headers)
    assert created.status_code == 201
    appeal = created.json()["data"]
    assert appeal["status"] == "pending"

    duplicate = client.post("/api/v1/appeals", json=_appeal_payload(detail, feedback), headers=student_headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == 40900

    teacher_headers = login_headers(client, "demo_teacher")
    teacher_list = client.get("/api/v1/teacher/appeals", headers=teacher_headers)
    assert teacher_list.status_code == 200
    assert len(teacher_list.json()["data"]) == 1

    teacher_detail = client.get(f"/api/v1/teacher/appeals/{appeal['id']}", headers=teacher_headers)
    assert teacher_detail.status_code == 200
    teacher_data = teacher_detail.json()["data"]
    assert teacher_data["essay_content"] == ESSAY_CONTENT
    assert teacher_data["evaluation"]["id"] == detail["id"]
    assert teacher_data["classification_suggestions"]

    other_teacher = User(
        username="other_teacher",
        password_hash=hash_password("OtherPass@2026"),
        display_name="其他教师",
        role=UserRole.TEACHER,
    )
    db_session.add(other_teacher)
    db_session.commit()
    other_token, _ = create_access_token(other_teacher.id, other_teacher.role)
    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert client.get(f"/api/v1/teacher/appeals/{appeal['id']}", headers=other_headers).status_code == 403

    review = client.post(
        f"/api/v1/teacher/appeals/{appeal['id']}/review",
        json={
            "decision": "adjust",
            "change_reason": "教师复核确认该表达属于有意设计，调整语言维度并保留学生风格。",
            "dimension_updates": [
                {"dimension": "content", "final_score": 4},
                {"dimension": "organization", "final_score": 4},
                {"dimension": "language", "final_score": 5},
            ],
            "feedback_changes": [
                {
                    "feedback_item_id": feedback["id"],
                    "action": "modified",
                    "content": "教师复核：该句属于有意表达，不应直接判为语言错误。",
                    "suggestion": "保留表达风格，仅检查指代是否清楚。",
                }
            ],
            "added_feedback": [
                {"dimension": "overall", "content": "教师补充：结合上下文评价个性表达。", "suggestion": "保留风格并优化衔接。"}
            ],
            "classification_codes": ["expression_misjudgment"],
            "classification_note": "教师确认 AI 对有意表达理解不足。",
            "revised_summary": "教师最终意见：保留个性表达，调整语言诊断。",
        },
        headers=teacher_headers,
    )
    assert review.status_code == 200, review.text
    assert review.json()["data"]["appeal_status"] == "accepted"

    db_session.expire_all()
    assert db_session.get(FeedbackItem, feedback["id"]).content == original_feedback
    assert db_session.get(Appeal, appeal["id"]).status == "accepted"
    scores = db_session.scalars(select(DimensionScore).where(DimensionScore.evaluation_id == detail["id"])).all()
    assert all(item.final_score is not None for item in scores)
    assert db_session.scalar(select(func.count(ReviewRecord.id))) == 1
    assert db_session.scalar(select(func.count(FeedbackReviewChange.id))) == 1
    assert db_session.scalar(select(func.count(TeacherFeedbackItem.id))) >= 1
    assert db_session.scalar(select(func.count(ReviewIssueTag.id))) == 1

    student_appeal = client.get("/api/v1/appeals", headers=student_headers).json()["data"][0]
    assert student_appeal["status"] == "accepted"
    assert len(student_appeal["review_records"]) == 1