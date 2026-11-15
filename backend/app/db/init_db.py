"""数据库初始化入口：自动建表，可独立执行 python -m app.db.init_db。"""
from app.core.config import BASE_DIR
from app.core.logging import get_logger
from app.db.session import SessionLocal, engine
from app.models import Base

logger = get_logger(__name__)

_ESSAY_COLUMN_MIGRATIONS = {
    "source_type": "ALTER TABLE essays ADD COLUMN source_type VARCHAR(20) NOT NULL DEFAULT 'text'",
    "image_path": "ALTER TABLE essays ADD COLUMN image_path VARCHAR(500)",
    "ocr_status": "ALTER TABLE essays ADD COLUMN ocr_status VARCHAR(20) NOT NULL DEFAULT 'none'",
    "ocr_text": "ALTER TABLE essays ADD COLUMN ocr_text TEXT",
    "essay_title": "ALTER TABLE essays ADD COLUMN essay_title VARCHAR(120)",
}

_WRITING_TASK_COLUMN_MIGRATIONS = {
    "prompt_id": "ALTER TABLE writing_tasks ADD COLUMN prompt_id INTEGER",
}


def _ensure_columns(table: str, migrations: dict[str, str]) -> None:
    with engine.begin() as connection:
        existing = {row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table})")}
        for column, ddl in migrations.items():
            if column not in existing:
                connection.exec_driver_sql(ddl)
                logger.info("%s 表已补列：%s", table, column)


def _ensure_essay_columns() -> None:
    """幂等补齐 essays 新增列；create_all 不会给已存在的表加列。"""
    _ensure_columns("essays", _ESSAY_COLUMN_MIGRATIONS)


def _ensure_writing_task_columns() -> None:
    _ensure_columns("writing_tasks", _WRITING_TASK_COLUMN_MIGRATIONS)


def init_database() -> None:
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _ensure_essay_columns()
    _ensure_writing_task_columns()
    logger.info("数据库表结构初始化完成，共 %s 张表", len(Base.metadata.tables))


if __name__ == "__main__":
    from app.db.seed import seed_demo_data

    init_database()
    with SessionLocal() as db:
        created = seed_demo_data(db)
    print("演示数据初始化完成" if created else "数据库已有数据，跳过演示数据初始化")