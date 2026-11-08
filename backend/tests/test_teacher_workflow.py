"""教师多申诉复核、争议统计、规则建议审批与版本发布测试。"""
from sqlalchemy import select

from app.models.rubric import RubricVersion
from tests.conftest import create_completed_evaluation, login_headers

CONTENT_TEMPLATE = (
    "评价需要依据，也需要允许作者说明表达意图。{marker}\n\n"
    "例如，在课堂讨论中，我先核对材料来源，再解释材料与观点之间的关系，避免只用结论代替分析。\n\n"
    "因此，我会保留个人表达风格，同时根据证据调整论据和段落衔接。"
)


def _appeal_for_detail(client, headers, detail):
    feedback = next(item for item in detail["feedback_items"] if any(e["verified_status"] == "verified" for e in item["evidence"]))
    evidence = next(item for item in feedback["evidence"] if item["verified_status"] == "verified")
    response = client.post(
        "/api/v1/appeals",
        json={
            "evaluation_id": detail["id"],
            "feedback_item_id": feedback["id"],
            "reason_type": "creative_expression_misjudged",
            "dimension": feedback["dimension"] if feedback["dimension"] in {"content", "organization", "language", "overall", "topic"} else "overall",
            "description": "这段表达是我有意的个人风格，希望教师结合原文核查是否存在误判。",
            "evidence": evidence,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_similar_disputes_generate_proposal_and_publish_tested_version(client, db_session, evaluation_runner):
    details = []
    for index, username in enumerate(("demo_student", "demo_student2", "demo_student3"), start=1):
        headers = login_headers(client, username)
        _, detail = create_completed_evaluation(
            client, headers, evaluation_runner, CONTENT_TEMPLATE.format(marker=f"样本{index}")
        )
        _appeal_for_detail(client, headers, detail)
        details.append(detail)

    teacher_headers = login_headers(client, "demo_teacher")
    appeals = client.get("/api/v1/teacher/appeals", headers=teacher_headers).json()["data"]
    assert len(appeals) == 3

    for index, appeal in enumerate(appeals):
        payload = {
            "decision": "adjust" if index == 0 else "uphold",
            "change_reason": "教师复核依据原文证据完成判断，结论和理由均进入复核记录。",
            "dimension_updates": (
                [
                    {"dimension": "content", "final_score": 4},
                    {"dimension": "organization", "final_score": 4},
                    {"dimension": "language", "final_score": 4},
                ]
                if index == 0
                else []
            ),
            "feedback_changes": [],
            "added_feedback": [],
            "classification_codes": ["expression_misjudgment"],
            "classification_note": "教师确认表达误判类别。",
            "revised_summary": None,
        }
        reviewed = client.post(
            f"/api/v1/teacher/appeals/{appeal['id']}/review", json=payload, headers=teacher_headers
        )
        assert reviewed.status_code == 200, reviewed.text

    stats = client.get("/api/v1/teacher/analytics/appeal-patterns?days=30", headers=teacher_headers)
    assert stats.status_code == 200
    assert stats.json()["data"]["sample_count"] == 3
    assert stats.json()["data"]["tag_counts"][0]["tag_code"] == "expression_misjudgment"
    assert stats.json()["data"]["tag_counts"][0]["count"] == 3

    proposals = client.get("/api/v1/teacher/rule-proposals", headers=teacher_headers).json()["data"]
    if not proposals:
        generated = client.post("/api/v1/teacher/rule-proposals/generate?window_days=30", headers=teacher_headers)
        assert generated.status_code == 200
        proposals = client.get("/api/v1/teacher/rule-proposals", headers=teacher_headers).json()["data"]
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["source_tag"] == "expression_misjudgment"
    assert len(proposal["related_appeal_ids"]) == 3
    assert proposal["typical_cases"]

    approved = client.post(
        f"/api/v1/teacher/rule-proposals/{proposal['id']}/approve",
        json={
            "decision_note": "教研组同意澄清表达类评价要求。",
            "title": proposal["title"],
            "problem_description": proposal["problem_description"],
            "suggestion": "评价非标准表达时先说明语境和判断依据，并提供保留风格的修改方式。",
            "expected_effect": "减少表达误判争议，需用发布后的真实复核记录验证。",
            "rule_content": "语言维度应区分表达错误与有意风格，不得仅因句式非常规直接判错。",
            "change_reason": "依据 3 条教师确认的表达误判记录，澄清语言维度评价要求。",
        },
        headers=teacher_headers,
    )
    assert approved.status_code == 200, approved.text
    version = approved.json()["data"]
    assert version["status"] == "testing"

    regression = client.post(
        f"/api/v1/teacher/rubric-versions/{version['id']}/regression-test", headers=teacher_headers
    )
    assert regression.status_code == 200
    assert regression.json()["data"]["status"] == "passed"
    assert regression.json()["data"]["mode"] == "structure_and_history_only"

    published = client.post(
        f"/api/v1/teacher/rubric-versions/{version['id']}/publish", headers=teacher_headers
    )
    assert published.status_code == 200
    assert published.json()["data"]["status"] == "published"

    db_session.expire_all()
    versions = {item.id: item for item in db_session.scalars(select(RubricVersion)).all()}
    assert versions[version["id"]].status == "published"
    assert versions[1].status == "archived"

    student_headers = login_headers(client, "demo_student")
    essay_response = client.post(
        "/api/v1/essays",
        json={"prompt_id": 1, "content": CONTENT_TEMPLATE.format(marker="新版本绑定"), "submission_mode": "submit"},
        headers=student_headers,
    )
    evaluation = client.post(f"/api/v1/evaluations/{essay_response.json()['data']['id']}", headers=student_headers)
    assert evaluation.status_code == 201
    assert evaluation.json()["data"]["rubric_version_id"] == version["id"]