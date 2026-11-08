"""真实模型结构化输出诊断：不输出密钥，只输出 finish_reason、长度和尾部片段。"""
import json

import httpx

from app.agents.llm_client import AgentLLMClient

original_post = httpx.Client.post
calls: list[dict] = []


def wrapped_post(self, url, **kwargs):
    response = original_post(self, url, **kwargs)
    try:
        body = response.json()
        choice = body["choices"][0]
        content = choice["message"].get("content") or ""
        calls.append(
            {
                "status": response.status_code,
                "finish_reason": choice.get("finish_reason"),
                "content_length": len(content),
                "content_tail": content[-160:].replace("\n", " "),
                "usage": body.get("usage"),
            }
        )
    except Exception as exc:
        calls.append({"parse_error": str(exc)})
    return response


httpx.Client.post = wrapped_post
try:
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
        "diagnostic_rule": "仅输出1-5诊断等级",
    }
    try:
        result, _usage = AgentLLMClient().execute("language_agent", "评价语言规范、准确性与表现力", essay, [], [])
        print("RESULT", result.status, len(result.evidence))
    except Exception as exc:
        print("FINAL_ERROR", str(exc)[:300])
    print("CALLS", json.dumps(calls, ensure_ascii=False))
finally:
    httpx.Client.post = original_post