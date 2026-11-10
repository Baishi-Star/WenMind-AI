"""探测 DeepSeek 模型是否支持图片输入。

不输出任何密钥；仅打印 HTTP 状态、错误信息与模型返回内容片段。
"""
import base64
import json
from pathlib import Path

import httpx

from app.core.config import settings

SAMPLE = Path("../作文/mmexport1794135061713.jpg")


def build_payload(model: str, image_b64: str) -> dict:
    return {
        "model": model,
        "max_tokens": settings.llm_max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "这张图片里有一段中文手写文字，请只提取第一行文字，直接输出文字本身。"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            }
        ],
    }


def main() -> None:
    print("模型:", settings.llm_model)
    print("样例存在:", SAMPLE.exists())
    if not SAMPLE.exists():
        return
    image_b64 = base64.b64encode(SAMPLE.read_bytes()).decode("ascii")
    print("base64 长度:", len(image_b64))
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json=build_payload(settings.llm_model, image_b64),
        timeout=120,
    )
    print("HTTP:", response.status_code)
    text = response.text
    print("响应片段:", text[:600])
    try:
        body = response.json()
        message = body.get("choices", [{}])[0].get("message", {})
        print("content:", (message.get("content") or "")[:200])
        print("finish_reason:", body.get("choices", [{}])[0].get("finish_reason"))
        print("usage:", json.dumps(body.get("usage"), ensure_ascii=False))
    except Exception as exc:
        print("解析失败:", exc)


if __name__ == "__main__":
    main()