"""测试基础设施：每个测试使用独立临时 SQLite，不污染演示数据库。"""
import os

os.environ["AUTO_INIT_DB"] = "false"
os.environ["AUTO_SEED_DEMO"] = "false"
os.environ["PASSWORD_HASH_ITERATIONS"] = "10000"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db.init_db import Base
from app.db.seed import seed_demo_data
from app.db.session import build_engine, get_db
from app.main import app


@pytest.fixture()
def db_session(tmp_path):
    database_path = tmp_path / "wenmind_test.db"
    engine = build_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with testing_session() as session:
        seed_demo_data(session)
        yield session
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login_headers(client, username: str, password: str = "Demo@2026") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}