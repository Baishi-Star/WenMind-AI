"""批量重评 `作文/` 目录下的全部图片作文：上传 → 识别 → 提交 → 评价 → 记录。

串行执行以避免上游限流；每篇结果即时写入审计文件，失败不阻塞后续。
"""
import datetime
import io
import json
import time
from pathlib import Path

import httpx
from PIL import Image

CFG = {}
for line in io.open(".env", encoding="utf-8"):
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and "=" in stripped:
        key, _, value = stripped.partition("=")
        CFG[key] = value

BASE = "http://127.0.0.1:8000/api/v1"
PASSWORD = CFG.get("DEMO_PASSWORD", "") or "Demo@2026"
IMAGE_DIR = Path("../作文")
AUDIT_DIR = Path("data/audit")
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
PROGRESS_FILE = AUDIT_DIR / f"reevaluation-{STAMP}.json"

client = httpx.Client(timeout=60)
login = client.post(f"{BASE}/auth/login", json={"username": "demo_student", "password": PASSWORD})
headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

prompts = client.get(f"{BASE}/essays/prompts", headers=headers).json()["data"]
prompt = next((item for item in prompts if "邻里" in item["title"]), prompts[0])
images = sorted(IMAGE_DIR.glob("*.jpg"))

results = []
print(f"START prompts={len(prompts)} prompt_id={prompt['id']} images={len(images)}", flush=True)

for index, image in enumerate(images, 1):
    entry = {"index": index, "image": image.name, "status": "started"}
    try:
        image_bytes = image.read_bytes()
        try:
            with Image.open(image) as source:
                thumbnail = source.convert("RGB")
                thumbnail.thumbnail((1280, 1280), Image.LANCZOS)
                buffer = io.BytesIO()
                thumbnail.save(buffer, format="JPEG", quality=85)
            image_bytes = buffer.getvalue()
        except Exception:  # noqa: BLE001 - 压缩失败则用原图
            image_bytes = image.read_bytes()
        uploaded = client.post(
            f"{BASE}/essays/upload-image",
            headers=headers,
            files={"image": (image.name, image_bytes, "image/jpeg")},
        )
        entry["upload_http"] = uploaded.status_code
        token = uploaded.json()["data"]["image_token"]
        entry["image_token"] = token

        ocr = None
        for ocr_attempt in range(1, 3):
            try:
                ocr = client.post(
                    f"{BASE}/essays/ocr", headers=headers, json={"image_token": token}, timeout=600
                ).json()["data"]
                if ocr.get("status") == "parsed" and ocr.get("text", "").strip():
                    break
            except httpx.ReadTimeout:
                ocr = {"status": "timeout", "text": ""}
            time.sleep(5)
        entry["ocr_status"] = ocr.get("status") if ocr else "timeout"
        if not ocr or ocr.get("status") != "parsed" or not ocr.get("text", "").strip():
            entry["status"] = "ocr_failed"
            results.append(entry)
            PROGRESS_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{index}/{len(images)}] OCR_FAILED {image.name}", flush=True)
            continue

        text = ocr["text"]
        essay = client.post(
            f"{BASE}/essays",
            headers=headers,
            json={
                "prompt_id": prompt["id"],
                "content": text[:20000],
                "submission_mode": "submit",
                "source_type": "image",
                "image_path": token,
                "ocr_text": text,
            },
        ).json()["data"]
        entry["essay_id"] = essay["id"]
        evaluation_id = None
        detail = None
        attempts = []
        for attempt in range(1, 4):
            evaluation_id = client.post(f"{BASE}/evaluations/{essay['id']}", headers=headers).json()["data"]["id"]
            detail = None
            for _ in range(150):
                time.sleep(8)
                detail = client.get(f"{BASE}/evaluations/{evaluation_id}", headers=headers).json()["data"]
                if detail["status"] in ("completed", "failed"):
                    break
            attempts.append(
                {
                    "attempt": attempt,
                    "evaluation_id": evaluation_id,
                    "status": detail["status"] if detail else "timeout",
                }
            )
            if detail and detail["status"] == "completed":
                break
        entry["evaluation_id"] = evaluation_id
        entry["attempts"] = attempts
        entry["status"] = detail["status"] if detail else "timeout"
        if detail:
            entry["score"] = detail.get("original_total_score")
            entry["dimensions"] = [
                [item["dimension"], item["original_score"], item["max_score"]]
                for item in detail.get("dimension_scores", [])
            ]
            entry["error_message"] = detail.get("error_message")
    except Exception as exc:  # noqa: BLE001 - 单篇失败不影响后续
        entry["status"] = "error"
        entry["error"] = type(exc).__name__
    results.append(entry)
    PROGRESS_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[{index}/{len(images)}] {entry.get('status')} {image.name} score={entry.get('score')}",
        flush=True,
    )

print(f"DONE total={len(results)} file={PROGRESS_FILE}", flush=True)