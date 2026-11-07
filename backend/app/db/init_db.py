"""数据库初始化入口：自动建表，可独立执行 python -m app.db.init_db。"""
from app.core.config import BASE_DIR
from app.core.logging import get_logger
from app.db.session import SessionLocal, engine
from app.models import Base

logger = get_logger(__name__)


def init_database() -> None:
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表结构初始化完成，共 %s 张表", len(Base.metadata.tables))


if __name__ == "__main__":
    from app.db.seed import seed_demo_data

    init_database()
    with SessionLocal() as db:
        created = seed_demo_data(db)
    print("演示数据初始化完成" if created else "数据库已有数据，跳过演示数据初始化")