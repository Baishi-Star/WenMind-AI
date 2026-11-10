"""验证 AgentLLMClient.transcribe_image 真实识别作文图片。

不输出密钥；只打印识别文本长度与片段。
"""
from pathlib import Path

from app.agents.llm_client import AgentLLMClient

SAMPLE = Path("../作文/mmexport1794135061713.jpg")


def main() -> None:
    client = AgentLLMClient()
    print("执行模式:", client.execution_mode, "| 模型:", client.model_name)
    text, usage = client.transcribe_image(SAMPLE, "image/png")
    print("识别文本长度:", len(text))
    print("识别片段:", text[:200].replace("\n", " / "))
    if usage:
        print("usage:", {k: usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens")})


if __name__ == "__main__":
    main()