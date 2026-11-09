"""应用配置：所有环境相关参数统一从环境变量或 .env 读取。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "WenMind AI"
    app_version: str = "0.3.0"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'wenmind.db').as_posix()}"
    auto_init_db: bool = True
    auto_seed_demo: bool = True

    jwt_secret_key: str = ""
    demo_password: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    password_hash_iterations: int = 600000
    essay_max_chars: int = 20000

    llm_mock_mode: bool = True
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 60
    llm_json_mode: bool = False
    llm_max_tokens: int = 8192

    embedding_mode: str = "auto"
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""
    embedding_timeout_seconds: int = 60
    knowledge_upload_max_mb: int = 10
    knowledge_chunk_target_chars: int = 300
    knowledge_chunk_max_chars: int = 500

    rule_proposal_min_cases: int = 3
    rule_proposal_window_days: int = 30

    growth_min_samples: int = 3
    growth_recent_window: int = 3
    growth_weak_threshold: float = 3.5

    task_max_questions: int = 20
    task_max_due_days: int = 180

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def llm_configured(self) -> bool:
        """仅用于健康检查展示配置完整度，绝不返回密钥本身。"""
        return bool(self.llm_base_url and self.llm_api_key and self.llm_model)

    @property
    def llm_mode(self) -> str:
        return "mock" if self.llm_mock_mode else "remote"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()