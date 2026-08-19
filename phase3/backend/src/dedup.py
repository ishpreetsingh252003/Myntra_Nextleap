"""Phase 3 deduplication — exact + near-duplicate removal (EC-10, EC-11).

- Exact: normalized-text hash (keeps one representative per unique cleaned text).
- Near-dup: shingle-set (4-gram word/char shingles) Jaccard similarity with a
  threshold; the first-seen record stays the representative, later ones are
  marked `is_duplicate_of`. Works offline. An optional ChromaDB/embedding path
  can be slotted in via `Embedder` without changing the pipeline interface.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from .cleaning import normalize_text


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).casefold().encode("utf-8")).hexdigest()[:16]


def _shingles(text: str, k: int = 4) -> set[str]:
    norm = normalize_text(text).casefold()
    if len(norm) < k:
        return {norm}
    return {norm[i : i + k] for i in range(len(norm) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


@dataclass
class NearDupIndex:
    """Keeps clean-text representatives and finds near-duplicates for a new text."""

    threshold: float = 0.82
    shingle_size: int = 4
    exemplars: list[tuple[str, str]] = field(default_factory=list)  # (text, id)

    def add(self, clean_text: str, record_id: str) -> None:
        self.exemplars.append((clean_text, record_id))

    def find(self, clean_text: str) -> str | None:
        """Return id of the nearest exemplar if similarity >= threshold, else None."""
        sh_new = _shingles(clean_text, self.shingle_size)
        best_id, best = None, 0.0
        for text, rid in self.exemplars:
            sim = jaccard(sh_new, _shingles(text, self.shingle_size))
            if sim > best:
                best, best_id = sim, rid
        return best_id if best >= self.threshold else None

    def __len__(self) -> int:
        return len(self.exemplars)


class Deduper:
    def __init__(self, cfg: dict[str, Any]):
        self.near_threshold = float(cfg.get("near_dup_threshold", 0.82))
        self.exact: dict[str, str] = {}          # text_hash -> record id
        self.near = NearDupIndex(self.near_threshold)
        self.exact_dups = 0
        self.near_dups = 0

    def dedup(self, record_id: str, clean_text: str) -> str | None:
        """Return duplicate-of id (None when this record stays the representative).
        Marks exact dup before near dup so identical text is always exact."""
        h = text_hash(clean_text)
        if h in self.exact:
            self.exact_dups += 1
            return self.exact[h]
        near_of = self.near.find(clean_text)
        if near_of:
            self.near_dups += 1
            return near_of
        self.exact[h] = record_id
        self.near.add(clean_text, record_id)
        return None