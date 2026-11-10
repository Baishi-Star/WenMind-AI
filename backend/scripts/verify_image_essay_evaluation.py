"""验证图片提交的作文仍能正常生成评价报告与证据（配合 Mock 模式快速执行）。"""
import io
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
ESSAY_ID = 26
client = httpx.Client(timeout=60)

login = client.post(f"{BASE}/auth/login", json={"username": "demo_student", "password": PASSWORD})
headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

created = client.post(f"{BASE}/evaluations/{ESSAY_ID}", headers=headers)
print("CREATE", created.status_code, created.json().get("message"))
evaluation_id = created.json()["data"]["id"]

detail = None
for _ in range(40):
    time.sleep(1)
    detail = client.get(f"{BASE}/evaluations/{evaluation_id}", headers=headers).json()["data"]
    if detail["status"] in ("completed", "failed"):
        break

print("EVAL_ID", evaluation_id, "STATUS", detail["status"])
print("SCORE", detail.get("original_total_score"))
print("DIMS", [(item["dimension"], item["original_score"], item["max_score"]) for item in detail["dimension_scores"]])
evidence = [ev for fb in detail["feedback_items"] for ev in fb["evidence"]]
print("FEEDBACK", len(detail["feedback_items"]), "EVIDENCE", len(evidence), "VERIFIED", sum(1 for ev in evidence if ev["verified_status"] == "verified"))
print("AGENT_RUNS", len(detail["agent_runs"]))
if detail.get("error_message"):
    print("ERROR", str(detail["error_message"])[:200])