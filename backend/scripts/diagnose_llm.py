"""真实模型结构化输出诊断：不输出密钥，只输出 finish_reason、长度和尾部片段。"""
import argparse
import json
import sqlite3
from pathlib import Path

import httpx

from app.agents.llm_client import AGENT_INSTRUCTIONS, AgentLLMClient

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "wenmind.db"
original_post = httpx.Client.post
calls: list[dict] = []


def wrapped_post(self, url, **kwargs):
    response = original_post(self, url, **kwargs)
    request_body = kwargs.get("json") or {}
    try:
        body = response.json()
        choice = body["choices"][0]
        message = choice.get("message") or {}
        content = message.get("content") or ""
        reasoning = message.get("reasoning_content") or ""
        usage = body.get("usage") or {}
        calls.append(
            {
                "status": response.status_code,
                "finish_reason": choice.get("finish_reason"),
                "content_len": len(content),
                "reasoning_len": len(reasoning),
                "content_tail": content[-120:].replace("\n", " "),
                "request_max_tokens": request_body.get("max_tokens"),
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                    "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                },
            }
        )
    except Exception as exc:
        calls.append(
            {
                "status": getattr(response, "status_code", None),
                "parse_error": str(exc),
                "body_tail": (response.text or "")[-300:].replace("\n", " "),
            }
        )
    return response


httpx.Client.post = wrapped_post
try:
    parser = argparse.ArgumentParser(description="真实模型结构化输出诊断")
    parser.add_argument("--agent", default="content_agent")
    parser.add_argument("--essay-id", type=int, default=None, help="从本地库只读加载真实作文复现")
    args = parser.parse_args()

    if args.essay_id:
        conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "select e.id, e.content, e.content_version, p.title, p.requirements, r.dimensions_json "
            "from essays e left join essay_prompts p on p.id = e.prompt_id "
            "left join rubric_versions r on r.id = p.rubric_version_id where e.id = ?",
            (args.essay_id,),
        ).fetchone()
        conn.close()
        if row is None:
            raise SystemExit(f"作文 {args.essay_id} 不存在")
        essay = {
            "essay_id": row["id"],
            "content_version": row["content_version"],
            "title": row["title"] or "自由作文",
            "requirements": row["requirements"] or "",
            "content": row["content"] or "",
            "rubric": json.loads(row["dimensions_json"]) if row["dimensions_json"] else None,
            "diagnostic_rule": "按维度输出 0-20 整数分与四等第",
        }
        print("ESSAY", args.essay_id, "content_len=", len(essay["content"]), "requirements_len=", len(essay["requirements"]))
    else:
        essay = {
            "essay_id": 0,
            "content_version": 1,
            "title": "信息时代的独立思考",
            "requirements": "围绕信息时代的独立思考写议论文",
            "content": (
                "信息每天都在涌来，真正稀缺的是判断能力。我会先核对来源，再比较不同立场，"
                "最后根据证据修正自己的观点。因此，独立思考不是拒绝他人意见，而是保留被事实说服的勇气。"
            ),
            "rubric": None,
            "diagnostic_rule": "按维度输出 0-20 整数分与四等第",
        }
    try:
        result, _usage = AgentLLMClient().execute(args.agent, AGENT_INSTRUCTIONS[args.agent], essay, [], [])
        print("RESULT", result.status, len(result.evidence))
    except Exception as exc:
        print("FINAL_ERROR", str(exc)[:300])
    print("CALLS", json.dumps(calls, ensure_ascii=False))
finally:
    httpx.Client.post = original_post