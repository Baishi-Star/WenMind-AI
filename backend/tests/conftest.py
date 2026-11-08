"""测试基础设施：每个测试使用独立临时 SQLite，不污染演示数据库。"""
import os

os.environ["AUTO_INIT_DB"] = "false"
os.environ["AUTO_SEED_DEMO"] = "false"
os.environ["PASSWORD_HASH_ITERATIONS"] = "10000"
os.environ["DEMO_PASSWORD"] = "Demo@2026"
os.environ["LLM_MOCK_MODE"] = "true"
os.environ["EMBEDDING_MODE"] = "local_tfidf"

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
def client(db_session, monkeypatch):
    import app.api.evaluations as evaluations_api

    # 测试环境禁止后台任务使用生产 SessionLocal，避免污染或误跑真实数据库。
    monkeypatch.setattr(evaluations_api, "run_evaluation_task", lambda _evaluation_id: None)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def evaluation_runner(db_session):
    from app.agents.orchestrator import EvaluationOrchestrator

    def run(evaluation_id: int):
        EvaluationOrchestrator(db_session).run(evaluation_id)

    return run


def login_headers(client, username: str, password: str = "Demo@2026") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

def create_completed_evaluation(client, headers, evaluation_runner, content: str, prompt_id: int = 1):
    essay_response = client.post(
        "/api/v1/essays",
        json={"prompt_id": prompt_id, "content": content, "submission_mode": "submit"},
        headers=headers,
    )
    assert essay_response.status_code == 201, essay_response.text
    essay = essay_response.json()["data"]
    evaluation_response = client.post(f"/api/v1/evaluations/{essay['id']}", headers=headers)
    assert evaluation_response.status_code == 201, evaluation_response.text
    evaluation_id = evaluation_response.json()["data"]["id"]
    evaluation_runner(evaluation_id)
    detail_response = client.get(f"/api/v1/evaluations/{evaluation_id}", headers=headers)
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()["data"]
    assert detail["status"] == "completed", detail
    return essay, detail