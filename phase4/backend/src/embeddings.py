"""Per-conversation embeddings for Phase 5 clustering.

Default: TF-IDF vectors (offline, no API). When ChromaDB or OpenAI embeddings
are configured, those are used instead. Stored as JSON per conversation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Embedder:
    def __init__(self, cfg: dict[str, Any]):
        emb_cfg = cfg.get("embeddings", {})
        self.method = emb_cfg.get("method", "tfidf")
        self.max_features = int(emb_cfg.get("max_features", 500))
        self.ngram_range = tuple(emb_cfg.get("ngram_range", [1, 2]))
        self._vectorizer = None
        self._fitted = False

    def fit_transform(self, texts: list[str]) -> list[list[float]]:
        if self.method == "tfidf":
            return self._tfidf_fit_transform(texts)
        return [[0.0] * self.max_features for _ in texts]

    def transform(self, texts: list[str]) -> list[list[float]]:
        if self.method == "tfidf" and self._fitted:
            return self._tfidf_transform(texts)
        return self.fit_transform(texts)

    def _tfidf_fit_transform(self, texts: list[str]) -> list[list[float]]:
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            stop_words="english",
            sublinear_tf=True,
        )
        mat = self._vectorizer.fit_transform(texts)
        self._fitted = True
        return mat.toarray().tolist()

    def _tfidf_transform(self, texts: list[str]) -> list[list[float]]:
        mat = self._vectorizer.transform(texts)  # type: ignore
        return mat.toarray().tolist()

    def embedding_dim(self) -> int:
        if self.method == "tfidf" and self._vectorizer:
            return len(self._vectorizer.get_feature_names_out())
        return self.max_features


class EmbeddingStore:
    """Persists embeddings as JSONL alongside the extraction corpus."""

    def __init__(self, out_dir: Path):
        self.path = out_dir / "embeddings.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, conversation_id: str, embedding: list[float], metadata: dict[str, Any] | None = None) -> None:
        row = {"conversation_id": conversation_id, "embedding": [round(v, 6) for v in embedding]}
        if metadata:
            row["metadata"] = metadata
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def load_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()
