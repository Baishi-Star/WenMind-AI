"""对单篇已提交作文触发一次评价并等待完成（前台运行，用于断点续评验证）。"""
import io
import json
import os
import time

import httpx

CFG = {}
for line in io.open(".env", encoding="utf-8"):
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and "=" in stripped:
        key, _, value = stripped.partition("=")
        CFG[key] = value

BASE = "http://127.0.0.1:8000/api/v1"
PASSWORD = CFG.get("DEMO_PASSWORD", "") or "Demo@2026"
ESSAY_ID = int(os.environ.get("ESSAY_ID", "29"))
client = httpx.Client(timeout=60)

login = client.post(f"{BASE}/auth/login", json={"username": "demo_student", "password": PASSWORD})
headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
created = client.post(f"{BASE}/evaluations/{ESSAY_ID}", headers=headers)
print("CREATE", created.status_code, created.json().get("message"), flush=True)
evaluation_id = created.json()["data"]["id"]

detail = None
for _ in range(180):
    time.sleep(8)
    detail = client.get(f"{BASE}/evaluations/{evaluation_id}", headers=headers).json()["data"]
    if detail["status"] in ("completed", "failed"):
        break

print("EVAL", evaluation_id, "STATUS", detail["status"], flush=True)
print("SCORE", detail.get("original_total_score"), flush=True)
print("DIMS", [(item["dimension"], item["original_score"], item["max_score"]) for item in detail["dimension_scores"]], flush=True)
if detail.get("error_message"):
    print("ERROR", str(detail["error_message"])[:300], flush=True)
print("DONE", json.dumps({"essay_id": ESSAY_ID, "evaluation_id": evaluation_id, "status": detail["status"]}), flush=True)