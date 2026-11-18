"""教师复核后写入 final_total_score，且不覆盖 AI 原始总分与维度原始分。"""
from app.core import scoring
from app.models.essay import Essay
from app.models.evaluation import Evaluation
from tests.conftest import create_completed_evaluation, login_headers


def _create_appeal(client, student_headers, evaluation_id, dimension):
    response = client.post(
        "/api/v1/appeals",
        headers=student_headers,
        json={
            "evaluation_id": evaluation_id,
            "reason_type": "score_low",
            "dimension": dimension,
            "description": "复核总分校准联动验证，请重新核定该维度得分。",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _review(client, teacher_headers, appeal_id, payload):
    response = client.post(
        f"/api/v1/teacher/appeals/{appeal_id}/review",
        headers=teacher_headers,
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_uphold_keeps_final_total_equal_to_original(client, db_session, evaluation_runner):
    student = login_headers(client, "demo_student")
    teacher = login_headers(client, "demo_teacher")
    _essay, detail = create_completed_evaluation(
        client, student, evaluation_runner, "维持原评价时最终总分应与 AI 原始总分一致。" * 12
    )
    original = detail["original_total_score"]
    appeal = _create_appeal(client, student, detail["id"], "content")
    _review(
        client,
        teacher,
        appeal["id"],
        {
            "decision": "uphold",
            "change_reason": "经核查维持 AI 原评价，不修改任何维度得分。",
            "classification_codes": ["scoring_bias"],
        },
    )
    db_session.expire_all()
    evaluation = db_session.get(Evaluation, detail["id"])
    assert evaluation.original_total_score == original
    assert evaluation.final_total_score == original


def test_adjust_updates_final_total_without_touching_original(client, db_session, evaluation_runner):
    student = login_headers(client, "demo_student")
    teacher = login_headers(client, "demo_teacher")
    essay, detail = create_completed_evaluation(
        client, student, evaluation_runner, "调整维度后最终总分应按校准规则联动变化。" * 12
    )
    original = detail["original_total_score"]
    originals = {item["dimension"]: item["original_score"] for item in detail["dimension_scores"]}
    appeal = _create_appeal(client, student, detail["id"], "content")
    _review(
        client,
        teacher,
        appeal["id"],
        {
            "decision": "adjust",
            "change_reason": "按 0-20 口径重新核定三维得分并联动最终总分。",
            "classification_codes": ["scoring_bias"],
            "dimension_updates": [
                {"dimension": name, "final_score": 20} for name in ("content", "expression", "development")
            ],
        },
    )
    db_session.expire_all()
    essay_row = db_session.get(Essay, essay["id"])
    deduction = scoring.compute_deduction(essay_row.char_count or len(essay_row.content or ""))
    expected = scoring.calibrate_total(60 - deduction)
    evaluation = db_session.get(Evaluation, detail["id"])
    assert evaluation.original_total_score == original
    assert evaluation.final_total_score == expected
    assert evaluation.final_total_score != original
    assert 36.0 <= evaluation.final_total_score <= 58.0
    for score in evaluation.dimension_scores:
        assert score.original_score == originals[score.dimension]