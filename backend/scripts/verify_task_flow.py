"""写作任务下发 → 学生可见 → 学生提交 端到端自检脚本。

用法：
    ./.venv/Scripts/python.exe scripts/verify_task_flow.py          # 跑完清理本次任务与提交
    ./.venv/Scripts/python.exe scripts/verify_task_flow.py --keep   # 保留本次验收数据

依赖：后端已在 127.0.0.1:8000 运行，且已初始化演示账号与已发布量规。
"""
import argparse
import io
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BACKEND_DIR / "data" / "wenmind.db"


def load_password() -> str:
    for line in io.open(BACKEND_DIR / ".env", encoding="utf-8"):
        stripped = line.strip()
        if stripped.startswith("DEMO_PASSWORD="):
            return stripped.partition("=")[2] or "Demo@2026"
    return "Demo@2026"


PASSWORD = load_password()
client = httpx.Client(timeout=60)
results: list[bool] = []


def step(name: str, ok: bool, detail: str = "") -> bool:
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" | {detail}" if detail else ""))
    results.append(ok)
    return ok


def error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        return f"HTTP {response.status_code} code={body.get('code')} message={body.get('message')}"
    except Exception:  # noqa: BLE001
        return f"HTTP {response.status_code} {response.text[:200]}"


def login(username: str) -> dict[str, str]:
    response = client.post(f"{BASE}/auth/login", json={"username": username, "password": PASSWORD})
    if response.status_code != 200:
        raise SystemExit(f"登录失败 {username}: {error_detail(response)}")
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def cleanup(task_id: int, essay_ids: list[int]) -> None:
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys=ON")
    for essay_id in essay_ids:
        connection.execute("DELETE FROM evaluations WHERE essay_id=?", (essay_id,))
        connection.execute("DELETE FROM essays WHERE id=?", (essay_id,))
    connection.execute("DELETE FROM writing_tasks WHERE id=?", (task_id,))
    connection.commit()
    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    connection.close()
    print(f"INFO 已清理任务 #{task_id}、提交及关联作文 {essay_ids}")
    if violations:
        print(f"WARN 清理后仍存在外键违规：{violations}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="保留本次创建的验收数据")
    args = parser.parse_args()

    teacher = login("demo_teacher")
    student = login("demo_student")
    student_id = client.get(f"{BASE}/auth/me", headers=student).json()["data"]["id"]

    rubrics = client.get(f"{BASE}/teacher/rubric-versions", headers=teacher).json()["data"]
    published = [item for item in rubrics if item["status"] == "published"]
    if not published:
        step("存在已发布评分量规", False, "未找到 published 量规")
        return 1
    rubric_id = published[0]["id"]

    prompt_text = "自检材料：围绕邻里关系写一篇议论文，观点明确。"
    due_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    payload = {
        "title": f"任务链路自检 {datetime.now().strftime('%H%M%S')}",
        "prompt_text": prompt_text,
        "requirements": "不少于 100 字，观点明确。",
        "rubric_version_id": rubric_id,
        "word_min": 0,
        "word_max": 0,
        "due_at": due_at,
        "targets": [{"target_type": "student", "target_id": student_id}],
        "questions": [
            {"label": "问题一", "question_text": "结合材料谈谈你的看法。", "answer_type": "text"}
        ],
    }
    created = client.post(f"{BASE}/teacher/tasks", json=payload, headers=teacher)
    if not step("教师创建任务草稿", created.status_code == 201, error_detail(created) if created.status_code != 201 else ""):
        return 1
    task = created.json()["data"]
    task_id = task["id"]
    step("草稿状态为 draft", task["status"] == "draft", f"status={task['status']}")
    step("任务已绑定命题", task["prompt_id"] is not None, f"prompt_id={task['prompt_id']}")

    published_resp = client.post(f"{BASE}/teacher/tasks/{task_id}/publish", headers=teacher)
    if not step("教师发布任务", published_resp.status_code == 200, error_detail(published_resp) if published_resp.status_code != 200 else ""):
        if not args.keep:
            cleanup(task_id, [])
        return 1
    step("发布后状态为 published", published_resp.json()["data"]["status"] == "published")

    student_tasks = client.get(f"{BASE}/student/tasks", headers=student)
    listed = student_tasks.json()["data"] if student_tasks.status_code == 200 else []
    target = next((item for item in listed if item["id"] == task_id), None)
    step("学生任务列表包含刚发布任务", target is not None, f"student_tasks={len(listed)}")
    if target is None:
        if not args.keep:
            cleanup(task_id, [])
        return 1
    step("学生任务含 prompt_text", target["prompt_text"] == prompt_text, repr(target["prompt_text"]))
    step("学生任务含 requirements", target["requirements"] == payload["requirements"])
    step("学生任务含 rubric 版本", target["rubric_version_id"] == rubric_id, f"rubric={target['rubric_version_id']}")
    step("学生任务含截止时间", target["due_at"] is not None, f"due_at={target['due_at']}")

    question_id = target["questions"][0]["id"]
    submission = client.post(
        f"{BASE}/student/submissions",
        json={"task_id": task_id, "answers": [{"question_id": question_id, "content": "这是学生提交的自检作文正文，用于验证任务链路。"}]},
        headers=student,
    )
    if not step("学生创建提交", submission.status_code == 201, error_detail(submission) if submission.status_code != 201 else ""):
        if not args.keep:
            cleanup(task_id, [])
        return 1
    submission_data = submission.json()["data"]
    answer = submission_data["answers"][0]
    essay_ids = [item["essay_id"] for item in submission_data["answers"] if item.get("essay_id")]
    step("提交生成作文记录", answer["essay_id"] is not None, f"essay_id={answer['essay_id']}")
    step("提交进入评价队列", answer["evaluation_id"] is not None, f"evaluation_id={answer['evaluation_id']}")

    teacher_view = client.get(f"{BASE}/teacher/tasks/{task_id}/submissions", headers=teacher)
    if not step("教师查询任务提交", teacher_view.status_code == 200, error_detail(teacher_view) if teacher_view.status_code != 200 else ""):
        if not args.keep:
            cleanup(task_id, essay_ids)
        return 1
    teacher_rows = teacher_view.json()["data"]
    matched = next((row for row in teacher_rows if row["student_id"] == student_id), None)
    step("教师能看到该学生提交", matched is not None, f"submissions={len(teacher_rows)}")
    if matched:
        print(
            f"INFO 提交详情 submission_id={matched['id']} student={matched['student_name']} "
            f"status={matched['status']} answers={matched['answer_count']}"
        )

    if args.keep:
        print(f"INFO 已保留验收数据 task_id={task_id} essay_ids={essay_ids}")
    else:
        cleanup(task_id, essay_ids)

    passed = all(results)
    print(f"SUMMARY {'ALL_PASS' if passed else 'HAS_FAIL'} {sum(results)}/{len(results)}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())