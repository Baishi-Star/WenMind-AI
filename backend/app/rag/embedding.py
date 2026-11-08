"""Embedding 独立适配层：远程语义向量与明确标注的本地 TF-IDF 词汇向量。"""
from pathlib import Path

import httpx
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode


class RemoteEmbeddingAdapter:
    mode = "openai_compatible"
    semantic = True

    def __init__(self, model: str | None = None) -> None:
        self.model_name = model or settings.embedding_model
        if not (settings.embedding_base_url and settings.embedding_api_key and self.model_name):
            raise AppError(
                "远程 Embedding 配置不完整，请设置 EMBEDDING_BASE_URL、EMBEDDING_API_KEY、EMBEDDING_MODEL",
                ErrorCode.UPSTREAM_UNAVAILABLE,
                503,
            )
        self.endpoint = f"{settings.embedding_base_url.rstrip('/')}/embeddings"

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        return self.embed(texts)

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors: list[list[float]] = []
        try:
            with httpx.Client(timeout=settings.embedding_timeout_seconds) as client:
                for start in range(0, len(texts), 16):
                    response = client.post(
                        self.endpoint,
                        headers={"Authorization": f"Bearer {settings.embedding_api_key}"},
                        json={"model": self.model_name, "input": texts[start : start + 16]},
                    )
                    response.raise_for_status()
                    payload = response.json()
                    vectors.extend(item["embedding"] for item in payload["data"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise AppError(
                "Embedding 服务调用失败，文档已标记为失败；不会用随机向量或静默降级冒充语义检索",
                ErrorCode.UPSTREAM_UNAVAILABLE,
                503,
            ) from exc
        if len(vectors) != len(texts) or not vectors:
            raise AppError("Embedding 服务返回数量不正确", ErrorCode.UPSTREAM_UNAVAILABLE, 503)
        array = np.asarray(vectors, dtype=np.float32)
        if array.ndim != 2 or not np.isfinite(array).all():
            raise AppError("Embedding 服务返回了无效向量", ErrorCode.UPSTREAM_UNAVAILABLE, 503)
        return array

    def save(self, _directory: Path) -> None:
        return None


class LocalTfidfAdapter:
    mode = "local_tfidf"
    semantic = False
    model_name = "tfidf-char-ngram-2-4"

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 4),
            min_df=1,
            max_features=4096,
            sublinear_tf=True,
            dtype=np.float32,
        )

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        return self.vectorizer.fit_transform(texts).toarray().astype(np.float32)

    def embed(self, texts: list[str]) -> np.ndarray:
        if not hasattr(self.vectorizer, "vocabulary_"):
            raise AppError("本地 TF-IDF 向量器尚未加载，请先重建知识库索引")
        return self.vectorizer.transform(texts).toarray().astype(np.float32)

    def save(self, directory: Path) -> None:
        joblib.dump(self.vectorizer, directory / "vectorizer.joblib")


def create_embedding_adapter():
    mode = settings.embedding_mode.lower()
    remote_configured = bool(settings.embedding_base_url and settings.embedding_api_key and settings.embedding_model)
    if mode == "remote" or (mode == "auto" and remote_configured):
        return RemoteEmbeddingAdapter()
    if mode in {"auto", "local_tfidf"}:
        return LocalTfidfAdapter()
    raise AppError("EMBEDDING_MODE 仅支持 auto、remote、local_tfidf")


def load_embedding_adapter(metadata: dict, directory: Path):
    if metadata.get("embedding_mode") == "local_tfidf":
        adapter = LocalTfidfAdapter()
        vectorizer_path = directory / "vectorizer.joblib"
        if not vectorizer_path.exists():
            raise AppError("本地向量器文件缺失，请重新索引知识库文档")
        adapter.vectorizer = joblib.load(vectorizer_path)
        return adapter
    if metadata.get("embedding_mode") == "openai_compatible":
        return RemoteEmbeddingAdapter(model=metadata.get("embedding_model"))
    raise AppError("无法识别知识库索引的向量化模式，请重新索引")