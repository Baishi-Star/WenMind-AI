"""图片作文文字识别服务。

不使用本地 OCR，直接调用兼容 OpenAI 的多模态视觉接口；
配置优先使用 ocr_*，留空时复用 llm_*。
"""
import base64
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

RECOGNITION_PROMPT = (
    "这是一张学生手写作文的答题卡或作文纸照片。请只输出图片中的作文正文文字，"
    "保留原文自然段分行；忽略印刷题目、分数、教师红笔批注和页眉页脚；"
    "不要纠错、不要润色、不要评价；不要输出“以下是识别结果”等任何说明文字；"
    "无法辨认的字用「□」代替，不要臆造内容。"
)


class OcrFailure(Exception):
    """识别失败，原始原因仅记录服务端日志，不返回给前端。"""


def is_enabled() -> bool:
    return settings.ocr_enabled


def _resolve_config() -> tuple[str, str, str]:
    base_url = (settings.ocr_base_url or settings.llm_base_url).rstrip("/")
    api_key = settings.ocr_api_key or settings.llm_api_key
    model = settings.ocr_model or settings.llm_model
    return base_url, api_key, model


def recognize(image_path: Path, mime_type: str) -> str:
    """识别图片文字，失败抛 OcrFailure（内部原因只写日志）。"""
    base_url, api_key, model = _resolve_config()
    if not (base_url and api_key and model):
        logger.warning("图片识别失败：视觉模型配置不完整")
        raise OcrFailure("config incomplete")
    if not image_path.exists():
        logger.warning("图片识别失败：文件不存在 %s", image_path.name)
        raise OcrFailure("image missing")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload = {
        "model": model,
        "max_tokens": settings.llm_vision_max_tokens,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": RECOGNITION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
                ],
            }
        ],
    }
    try:
        with httpx.Client(timeout=settings.ocr_timeout_seconds) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
    except Exception as exc:  # noqa: BLE001 - 统一转为可读失败，不向前端暴露原始异常
        logger.warning("图片识别请求异常：%s", type(exc).__name__)
        raise OcrFailure("request error") from exc
    if response.status_code != 200:
        logger.warning("图片识别上游状态异常：status=%s", response.status_code)
        raise OcrFailure(f"upstream {response.status_code}")
    try:
        content = response.json()["choices"][0]["message"].get("content") or ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("图片识别响应结构异常")
        raise OcrFailure("bad response") from exc
    text = content.strip()
    if not text:
        logger.warning("图片识别返回空文本")
        raise OcrFailure("empty text")
    return text

_END_PUNCTUATIONS = ("。", "！", "？", "；", "，", "、", "…", ".", "!", "?", ";", ",")
_STRUCTURE_PREFIXES = (
    "一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、", "九、", "十、",
    "（一）", "（二）", "（三）", "（四）",
    "1.", "2.", "3.", "4.", "①", "②", "③", "④",
    "第", "要求", "写作提示",
)
_PAIRED_DECORATIONS = (("《", "》"), ("“", "”"), ("‘", "’"), ("「", "」"), ("【", "】"))


def _clean_title(line: str) -> str:
    text = line.strip()
    changed = True
    while changed and text:
        changed = False
        for left, right in _PAIRED_DECORATIONS:
            if text.startswith(left) and text.endswith(right) and len(text) > len(left) + len(right):
                text = text[len(left) : -len(right)].strip()
                changed = True
    return text.lstrip("#").strip()


def extract_title_and_body(text: str) -> tuple[str | None, str]:
    """启发式提取首个非空行为标题；失败时返回 (None, 原文)。"""
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    first_index = next((index for index, line in enumerate(lines) if line.strip()), None)
    if first_index is None:
        return None, raw
    candidate = _clean_title(lines[first_index])
    if not (2 <= len(candidate) <= 40):
        return None, raw
    if candidate.endswith(_END_PUNCTUATIONS):
        return None, raw
    if any(candidate.startswith(prefix) for prefix in _STRUCTURE_PREFIXES):
        return None, raw
    if not candidate.strip("《》“”‘’「」【】# \t"):
        return None, raw
    if not any(line.strip() for line in lines[first_index + 1 :]):
        return None, raw
    body_lines = lines[:first_index] + lines[first_index + 1 :]
    return candidate, "\n".join(body_lines).strip("\n")