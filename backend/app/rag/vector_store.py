"""FAISS 向量索引：归一化余弦相似度、原子保存、重启加载与线程安全。"""
import json
import os
import threading
from pathlib import Path

import faiss
import numpy as np

from app.core.exceptions import AppError
from app.rag.embedding import load_embedding_adapter


class FaissVectorStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.index_path = directory / "index.faiss"
        self.metadata_path = directory / "index_meta.json"
        self._lock = threading.RLock()
        self._index = None
        self._metadata: dict = {}
        self._adapter = None
        self._loaded = False

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        vectors = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if (norms <= 0).any():
            raise AppError("文档向量存在零向量，无法建立有效索引")
        return vectors / norms

    def rebuild(self, chunks: list, adapter) -> dict | None:
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            if not chunks:
                self.clear()
                return None
            vectors = self._normalize(adapter.fit_transform([chunk.chunk_text for chunk in chunks]))
            index = faiss.IndexFlatIP(vectors.shape[1])
            index.add(vectors)
            metadata = {
                "embedding_mode": adapter.mode,
                "embedding_model": adapter.model_name,
                "semantic": adapter.semantic,
                "dimension": int(vectors.shape[1]),
                "chunk_ids": [chunk.id for chunk in chunks],
            }
            temporary_index = self.directory / "index.faiss.tmp"
            serialized_index = faiss.serialize_index(index)
            temporary_index.write_bytes(serialized_index.tobytes())
            os.replace(temporary_index, self.index_path)
            temporary_metadata = self.directory / "index_meta.json.tmp"
            temporary_metadata.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary_metadata, self.metadata_path)
            adapter.save(self.directory)
            self._index = index
            self._metadata = metadata
            self._adapter = adapter
            self._loaded = True
            return metadata

    def load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            if not (self.index_path.exists() and self.metadata_path.exists()):
                self._loaded = True
                return
            self._metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            self._index = faiss.deserialize_index(np.frombuffer(self.index_path.read_bytes(), dtype=np.uint8))
            if self._index.ntotal != len(self._metadata.get("chunk_ids", [])):
                raise AppError("FAISS 索引与切片映射数量不一致，请重新索引")
            self._adapter = load_embedding_adapter(self._metadata, self.directory)
            self._loaded = True

    def current_adapter(self):
        self.load()
        return self._adapter

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        with self._lock:
            self.load()
            if self._index is None or self._index.ntotal == 0:
                return []
            raw_vectors = self._adapter.embed([query])
            if raw_vectors.size == 0 or np.linalg.norm(raw_vectors[0]) <= 0:
                return []
            vector = self._normalize(raw_vectors)
            scores, positions = self._index.search(vector, min(top_k, self._index.ntotal))
            chunk_ids = self._metadata["chunk_ids"]
            return [
                (int(chunk_ids[position]), float(score))
                for position, score in zip(positions[0], scores[0], strict=True)
                if 0 <= position < len(chunk_ids) and float(score) > 0
            ]

    def status(self) -> dict:
        with self._lock:
            self.load()
            return {
                "indexed_chunks": int(self._index.ntotal) if self._index is not None else 0,
                "embedding_mode": self._metadata.get("embedding_mode"),
                "embedding_model": self._metadata.get("embedding_model"),
                "semantic": self._metadata.get("semantic"),
                "index_persisted": self.index_path.exists(),
            }

    def clear(self) -> None:
        with self._lock:
            for path in (self.index_path, self.metadata_path, self.directory / "vectorizer.joblib"):
                path.unlink(missing_ok=True)
            self._index = None
            self._metadata = {}
            self._adapter = None
            self._loaded = True