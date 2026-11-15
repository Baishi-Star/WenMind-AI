"""删除全部作文评分记录（保留作文原文），含备份、审计与完整性校验。"""
import datetime
import json
import shutil
import sqlite3
from pathlib import Path

DB = Path("data/wenmind.db")
BACKUP_DIR = Path("data/backups")
AUDIT_DIR = Path("data/audit")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUP_DIR / f"wenmind-{timestamp}.db"
shutil.copy2(DB, backup)

tables = [
    "review_records",
    "appeal_items",
    "appeals",
    "evaluation_questions",
    "retrieval_logs",
    "evaluation_reports",
    "agent_runs",
    "feedback_items",
    "dimension_scores",
    "evaluations",
]

connection = sqlite3.connect(DB)
connection.execute("PRAGMA foreign_keys=ON")
cursor = connection.cursor()
before = {table: cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
essays_before = cursor.execute("SELECT COUNT(*) FROM essays").fetchone()[0]

connection.execute("BEGIN")
for table in tables:
    cursor.execute(f"DELETE FROM {table}")
cursor.execute("UPDATE growth_snapshots SET evaluation_id=NULL")
cursor.execute("UPDATE training_task_details SET source_evaluation_ids_json='[]'")
cursor.execute("DELETE FROM growth_snapshots")
cursor.execute("DELETE FROM growth_profiles")
connection.commit()

after = {table: cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
essays_after = cursor.execute("SELECT COUNT(*) FROM essays").fetchone()[0]
foreign_key_violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
connection.close()

audit = {
    "timestamp": timestamp,
    "backup": str(backup),
    "before": before,
    "after": after,
    "essays_before": essays_before,
    "essays_after": essays_after,
    "foreign_key_violations": foreign_key_violations,
}
audit_file = AUDIT_DIR / f"deletion-{timestamp}.json"
audit_file.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(audit, ensure_ascii=False))