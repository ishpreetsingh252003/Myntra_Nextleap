"""Phase 3 pipeline: raw corpus -> clean -> dedup -> relevance -> funnel stats.

Run bookkeeping and per-stage counts mirror the filtering funnel:
collected -> cleaned -> deduplicated -> relevant (with quarantine tracked).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .cleaning import Cleaner, CleanedRecord
from .dedup import Deduper
from .relevance import RelevanceClassifier
from .storage import Storage

_EXTERNAL_ID_SAFE = re.compile(r"[^A-Za-z0-9_:-]")
UID = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
       "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]


def _counter() -> Iterator[str]:
    i = 0
    while True:
        n, rem = i, []
        while True:
            rem.append(UID[n % 26])
            n = n // 26 - 1
            if n < 0:
                break
        yield "".join(reversed(rem))
        i += 1


class Pipeline:
    def __init__(self, storage: Storage, cfg: dict[str, Any], run_id: str | None = None):
        self.storage = storage
        self.cfg = cfg
        self.run_id = run_id or f"p3_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        self.cleaner = Cleaner(cfg)
        self.classifier = RelevanceClassifier(cfg)
        self.deduper = Deduper(cfg.get("dedup", {}))
        self.per_source: dict[str, dict[str, int]] = {}
        self._ids = _counter()

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}-{next(self._ids)}"

    def _record(self, cleaned: CleanedRecord, run_metadata: dict[str, Any]) -> dict[str, Any]:
        raw = cleaned.raw
        rec = {
            "id": self._new_id("P3"),
            "source": str(raw.get("source", "unknown")),
            "source_external_id": str(raw.get("source_external_id", "")),
            "url": str(raw.get("url", "")),
            "author": raw.get("author"),
            "timestamp": raw.get("timestamp"),
            "text": raw.get("text", ""),
            "clean_text": cleaned.masked_text,
            "language": raw.get("language") or _detect_latin(raw.get("text", "")),
            "collected_at": run_metadata.get("collected_at"),
            "collection_raw_hash": raw.get("raw_hash"),
            "run_id": self.run_id,
            "flags": cleaned.flags,
        }
        return rec

    def run(self, records: Iterator[dict[str, Any]]) -> dict[str, Any]:
        self.storage.start_run(self.run_id)
        self.storage.reset_corpora()
        run_metadata = {"collected_at": datetime.now(timezone.utc).isoformat()}

        collected = cleaned = deduped = relevant = 0
        per_source_track: dict[str, dict[str, int]] = {}

        for raw in records:
            source = str(raw.get("source", "unknown"))
            track = per_source_track.setdefault(source, {"collected": 0, "cleaned": 0, "deduped": 0, "relevant": 0, "quarantined": 0})
            track["collected"] += 1
            collected += 1

            cr = self.cleaner.clean(raw)
            if not cr.kept:
                track["quarantined"] += 1
                self.storage.save_quarantine({
                    "id": self._new_id("Q"),
                    "source": source,
                    "url": str(raw.get("url", "")),
                    "author": raw.get("author"),
                    "timestamp": raw.get("timestamp"),
                    "clean_text": cr.clean_text,
                    "quarantine_tag": cr.quarantine_tag,
                    "quarantine_reason": cr.quarantine_reason,
                    "raw": raw,
                })
                continue

            rec = self._record(cr, run_metadata)
            cleaned += 1
            track["cleaned"] += 1

            dup_of = self.deduper.dedup(rec["id"], cr.clean_text)
            if dup_of:
                rec["is_duplicate_of"] = dup_of
                # duplicates still flow into clean corpus but flagged; they are
                # excluded from relevance (they are the same voice repeated).
                self.storage.save_clean(rec)
                continue

            rec["is_duplicate_of"] = None
            self.storage.save_clean(rec)
            deduped += 1
            track["deduped"] += 1

            verdict = self.classifier.classify(rec["clean_text"])
            if verdict["relevant"]:
                rec.update(verdict)
                self.storage.save_relevant(rec)
                relevant += 1
                track["relevant"] += 1

        self.per_source = per_source_track
        summary = (
            f"collected={collected} cleaned={cleaned} deduped={deduped} "
            f"relevant={relevant} exact_dups={self.deduper.exact_dups} "
            f"near_dups={self.deduper.near_dups}"
        )
        self.storage.finish_run(self.run_id, per_source_track, summary)
        tags = [r[0] for r in self.storage.conn.execute("SELECT DISTINCT quarantine_tag FROM quarantine")]
        return {
            "run_id": self.run_id,
            "collected": collected,
            "cleaned": cleaned,
            "deduped": deduped,
            "relevant": relevant,
            "exact_dups": self.deduper.exact_dups,
            "near_dups": self.deduper.near_dups,
            "quarantined": {tag: self.storage.count_quarantine(tag) for tag in tags},
            "per_source": per_source_track,
            "classifier_version": self.classifier.version,
            "llm_available": self.classifier.llm_available,
        }


def _detect_latin(text: str) -> str:
    """Rough language hint: en/hi@latin for Hinglish, hi (devanagari), other."""
    latin = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    total = sum(1 for ch in text if ch.isalpha())
    if total == 0:
        return "unknown"
    return "en" if latin / total > 0.6 else "hi"