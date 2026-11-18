"""60 分制总分校准：锚点映射、字数扣分封顶与报告公开口径。"""
from types import SimpleNamespace

import pytest

from app.agents.orchestrator import EvaluationOrchestrator
from tests.conftest import create_completed_evaluation, login_headers


def _results(base_total: int):
    remaining = base_total
    results = []
    for dimension in ("content", "expression", "development"):
        score = min(20, remaining)
        results.append(SimpleNamespace(dimension=dimension, diagnostic_score=score))
        remaining -= score
    return results


def _compose(db_session, base_total: int, word_count: int = 1000):
    essay = SimpleNamespace(char_count=word_count, content="字" * word_count)
    return EvaluationOrchestrator(db_session)._compose_total_score(essay, _results(base_total))


@pytest.mark.parametrize(
    ("base_total", "expected_total"),
    [(0, 36.0), (24, 44.0), (36, 50.0), (42, 53.0), (48, 56.0), (60, 58.0)],
)
def test_anchor_calibration_band(db_session, base_total, expected_total):
    total, calibration = _compose(db_session, base_total)
    assert total == expected_total
    assert calibration["raw_total"] == base_total
    assert calibration["scoring_calibration"]["deduction"] == 0
    assert 0 <= total <= 60


def test_short_essay_deduction_is_capped(db_session):
    total, calibration = _compose(db_session, 42, word_count=0)
    assert calibration["scoring_calibration"]["deduction"] == 4
    assert calibration["raw_total"] == 38
    assert total == 51.0
    assert 0 <= total <= 60


def test_word_deduction_steps(db_session):
    for word_count, expected_deduction in [(800, 0), (750, 0), (700, 1), (500, 3), (100, 4)]:
        _, calibration = _compose(db_session, 42, word_count=word_count)
        assert calibration["scoring_calibration"]["deduction"] == expected_deduction


def test_report_exposes_raw_total_and_calibration(client, evaluation_runner):
    headers = login_headers(client, "demo_student")
    _essay, detail = create_completed_evaluation(client, headers, evaluation_runner, "短作文用于验证校准报告字段。" * 10)
    report = detail["report"]["report"]
    assert detail["original_total_score"] is not None
    assert 0 <= detail["original_total_score"] <= 60
    assert report["raw_total"] is not None
    calibration = report["scoring_calibration"]
    assert calibration["anchor_raw"] == 36
    assert calibration["slope"] == 0.5
    assert calibration["min"] == 36.0
    assert calibration["max"] == 58.0
    assert "deduction" in calibration
    assert calibration["calibration_version"]
    assert "非三维简单相加" in report["diagnostic_notice"]