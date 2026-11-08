"""异常与安全边界：模型/向量服务、输入校验、证据、空索引和上传限制。"""
import json

import httpx
import pytest
from pydantic import ValidationError

from app.agents.evidence import verify_evidence_item
from app.agents.llm_client import AgentLLMClient
from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.rag.embedding import RemoteEmbeddingAdapter
from app.rag.vector_store import FaissVectorStore
from app.schemas.agent import AgentResult, EvidenceItem
from tests.conftest import login_headers


def test_empty_and_overlong_essay_are_rejected(client):
    headers = login_headers(client, "demo_student")
    empty = client.post("/api/v1/essays", json={"content": "   ", "submission_mode": "submit"}, headers=headers)
    assert empty.status_code == 422
    assert empty.json()["code"] == 42200

    overlong = client.post(
        "/api/v1/essays", json={"content": "文" * 20001, "submission_mode": "submit"}, headers=headers
    )
    assert overlong.status_code == 400
    assert overlong.json()["code"] == 40000
    assert "不能超过" in overlong.json()["message"]


def test_evidence_verification_rejects_fabricated_quote():
    content = "这是一段真实的作文原文，可以用于证据核验。"
    fabricated = verify_evidence_item(EvidenceItem(quote="不存在的句子"), content)
    assert fabricated.verified_status == "unverified"
    assert fabricated.match_type == "not_found"

    corrected = verify_evidence_item(EvidenceItem(quote="真实的作文原文", start_char=99, end_char=100), content)
    assert corrected.verified_status == "verified"
    assert corrected.match_type == "corrected_unique_match"
    assert content[corrected.start_char : corrected.end_char] == "真实的作文原文"

    empty = verify_evidence_item(EvidenceItem(quote="   "), content)
    assert empty.verified_status == "unverified"


def test_agent_output_schema_rejects_invalid_json_and_missing_fields():
    with pytest.raises(json.JSONDecodeError):
        AgentLLMClient._extract_json("这不是 JSON")
    with pytest.raises(ValidationError):
        AgentResult.model_validate({"agent_name": "topic_agent", "task": "分析"})
    parsed = AgentLLMClient._extract_json('```json\n{"ok": true}\n```')
    assert parsed == {"ok": True}

    normalized = AgentResult.model_validate(
        {
            "agent_name": "quality_agent",
            "task": "审核",
            "analysis": "发现结构化问题",
            "quality_issues": [
                {"type": "评价矛盾", "description": "分数与评语不一致", "involved_agents": ["content_agent"]}
            ],
        }
    )
    assert isinstance(normalized.quality_issues[0], str)
    assert "评价矛盾" in normalized.quality_issues[0]
    assert "content_agent" in normalized.quality_issues[0]

    content_score = AgentResult.model_validate(
        {
            "agent_name": "content_agent",
            "task": "内容评价",
            "analysis": "分析",
            "diagnostic_score": {"content": 3, "organization": 3, "language": 4},
        }
    )
    assert content_score.diagnostic_score == 3
    topic_score = AgentResult.model_validate(
        {
            "agent_name": "topic_agent",
            "task": "审题",
            "analysis": "分析",
            "diagnostic_score": {"content": 3, "organization": 3, "language": 4},
        }
    )
    assert topic_score.diagnostic_score is None


def test_remote_model_timeout_retries_once_then_reports_503(monkeypatch):
    monkeypatch.setattr(settings, "llm_mock_mode", False)
    monkeypatch.setattr(settings, "llm_base_url", "http://model.invalid/v1")
    monkeypatch.setattr(settings, "llm_api_key", "test-key-not-real")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    calls = {"count": 0}

    def timeout_post(_self, *_args, **_kwargs):
        calls["count"] += 1
        raise httpx.TimeoutException("simulated timeout")

    monkeypatch.setattr(httpx.Client, "post", timeout_post)
    with pytest.raises(AppError) as error:
        AgentLLMClient().execute("topic_agent", "审题分析", {"content": "真实作文正文"}, [], [])
    assert calls["count"] == 2
    assert error.value.code == ErrorCode.UPSTREAM_UNAVAILABLE
    assert error.value.http_status == 503


def test_remote_embedding_without_configuration_fails_explicitly(monkeypatch):
    monkeypatch.setattr(settings, "embedding_base_url", "")
    monkeypatch.setattr(settings, "embedding_api_key", "")
    monkeypatch.setattr(settings, "embedding_model", "")
    with pytest.raises(AppError) as error:
        RemoteEmbeddingAdapter()
    assert error.value.code == ErrorCode.UPSTREAM_UNAVAILABLE
    assert "配置不完整" in error.value.message


def test_empty_knowledge_vector_store_returns_no_results(tmp_path):
    store = FaissVectorStore(tmp_path / "empty_index")
    assert store.search("作文评价标准", top_k=3) == []
    assert store.status()["indexed_chunks"] == 0


def test_knowledge_upload_rejects_unsupported_and_oversized_files(client, monkeypatch):
    headers = login_headers(client, "demo_admin")
    unsupported = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("malware.exe", b"not-a-document", "application/octet-stream")},
        headers=headers,
    )
    assert unsupported.status_code == 400
    assert unsupported.json()["code"] == 40000

    monkeypatch.setattr(settings, "knowledge_upload_max_mb", 0)
    oversized = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("essay.txt", b"content", "text/plain")},
        headers=headers,
    )
    assert oversized.status_code == 400
    assert "不能超过" in oversized.json()["message"]