"""图片作文最小闭环端到端验证：上传 → 识别 → 校对提交 → 非法输入拒绝。"""
import io
import json
from pathlib import Path

import httpx

CFG = {}
for line in io.open(".env", encoding="utf-8"):
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and "=" in stripped:
        key, _, value = stripped.partition("=")
        CFG[key] = value

BASE = "http://127.0.0.1:8000/api/v1"
PASSWORD = CFG.get("DEMO_PASSWORD", "") or "Demo@2026"
client = httpx.Client(timeout=180)

login = client.post(f"{BASE}/auth/login", json={"username": "demo_student", "password": PASSWORD})
print("LOGIN", login.status_code)
headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

status = client.get(f"{BASE}/essays/ocr/status", headers=headers)
print("OCR_STATUS", status.status_code, status.json()["data"])

image_bytes = Path("../作文/mmexport1794135091178.jpg").read_bytes()
upload = client.post(
    f"{BASE}/essays/upload-image",
    headers=headers,
    files={"image": ("essay.png", image_bytes, "image/png")},
)
print("UPLOAD", upload.status_code)
upload_data = upload.json()["data"]
print("UPLOAD_DATA", json.dumps(upload_data, ensure_ascii=False)[:300])
token = upload_data["image_token"]

ocr = client.post(f"{BASE}/essays/ocr", headers=headers, json={"image_token": token})
ocr_data = ocr.json()["data"]
print("OCR", ocr.status_code, "status=", ocr_data["status"], "len=", len(ocr_data["text"]))
text = ocr_data["text"]

content = text[:1500] if text.strip() else "图片作文校对后的正文测试内容。"
submit = client.post(
    f"{BASE}/essays",
    headers=headers,
    json={
        "prompt_id": 4,
        "content": content,
        "submission_mode": "submit",
        "source_type": "image",
        "image_path": token,
        "ocr_text": text,
    },
)
print("SUBMIT", submit.status_code)
submit_data = submit.json()["data"]
print(
    "SUBMIT_DATA",
    "essay_id=", submit_data["id"],
    "source_type=", submit_data["source_type"],
    "image_path=", submit_data["image_path"],
    "ocr_status=", submit_data["ocr_status"],
)

txt_reject = client.post(
    f"{BASE}/essays/upload-image",
    headers=headers,
    files={"image": ("a.txt", b"hello", "text/plain")},
)
print("TXT_REJECT", txt_reject.status_code, txt_reject.json().get("message"))

big_reject = client.post(
    f"{BASE}/essays/upload-image",
    headers=headers,
    files={"image": ("big.png", b"\x89PNG\r\n\x1a\n" + b"0" * (6 * 1024 * 1024), "image/png")},
)
print("BIG_REJECT", big_reject.status_code, big_reject.json().get("message"))

print("ESSAY_ID", submit_data["id"])