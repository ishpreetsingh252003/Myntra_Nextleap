"""Phase 3 storage — SQLite mirror + JSONL corpora + run bookkeeping."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS quarantine (
    id TEXT PRIMARY KEY, source TEXT, url TEXT, author TEXT, timestamp TEXT,
    clean_text TEXT, quarantine_tag TEXT, quarantine_reason TEXT, raw_json TEXT
);
CREATE TABLE IF NOT EXISTS clean_conversations (
    id TEXT PRIMARY KEY, source TEXT, source_external_id TEXT, url TEXT,
    author TEXT, timestamp TEXT, text TEXT, masked_task_restricted INTEGER DEFAULT 0,
    collection_raw_hash TEXT, is_duplicate_of TEXT, clean_text TEXT,
    language TEXT, collected_at TEXT,
    UNIQUE(source, source_external_id)
);
CREATE TABLE IF NOT EXISTS relevant_conversations (
    id TEXT PRIMARY KEY, source TEXT, source_external_id TEXT, url TEXT,
    author TEXT, timestamp TEXT, text TEXT, clean_text TEXT, language TEXT,
    collected_at TEXT, relevance_category TEXT, relevance_reason TEXT,
    relevance_confidence TEXT, decision_source TEXT, model TEXT, classifier_version TEXT,
    is_duplicate_of TEXT,
    UNIQUE(source, source_external_id)
);
CREATE TABLE IF NOT EXISTS funnel_runs (
    run_id TEXT PRIMARY KEY, started_at TEXT, finished_at TEXT, status TEXT,
    per_source TEXT, summary TEXT
);
"""


class Storage:
    def __init__(self, out_dir: Path, db_path: Path | None = None):
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (out_dir / "phase3.sqlite3")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self.clean_jsonl = out_dir / "clean_corpus.jsonl"
        self.relevant_jsonl = out_dir / "relevant_corpus.jsonl"
        self.quarantine_jsonl = out_dir / "quarantine.jsonl"

    # ---- writes ----
    def save_clean(self, rec: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO clean_conversations
               (id, source, source_external_id, url, author, timestamp, text,
                collection_raw_hash, is_duplicate_of, clean_text, language, collected_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rec["id"], rec["source"], rec["source_external_id"], rec["url"], rec["author"],
             rec["timestamp"], rec["text"], rec.get("collection_raw_hash"), rec["is_duplicate_of"],
             rec.get("clean_text", rec["text"]), rec.get("language"), rec.get("collected_at")),
        )
        with open(self.clean_jsonl, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def save_relevant(self, rec: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO relevant_conversations
               (id, source, source_external_id, url, author, timestamp, text, clean_text,
                language, collected_at, relevance_category, relevance_reason,
                relevance_confidence, decision_source, model, classifier_version, is_duplicate_of)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rec["id"], rec["source"], rec["source_external_id"], rec["url"], rec["author"],
             rec["timestamp"], rec["text"], rec.get("clean_text", rec["text"]), rec.get("language"),
             rec.get("collected_at"), rec["relevance_category"], rec["relevance_reason"],
             rec["relevance_confidence"], rec["decision_source"], rec["model"],
             rec["classifier_version"], rec.get("is_duplicate_of")),
        )
        with open(self.relevant_jsonl, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def save_quarantine(self, rec: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO quarantine
               (id, source, url, author, timestamp, clean_text, quarantine_tag,
                quarantine_reason, raw_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (rec["id"], rec["source"], rec["url"], rec["author"], rec["timestamp"],
             rec["clean_text"], rec["quarantine_tag"], rec["quarantine_reason"],
             json.dumps(rec.get("raw", {}), ensure_ascii=False, default=str)),
        )
        with open(self.quarantine_jsonl, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

    def reset_corpora(self) -> None:
        # reset_jsonl: fresh run should not double-append
        for p in (self.clean_jsonl, self.relevant_jsonl, self.quarantine_jsonl):
            if p.exists():
                p.unlink()
        for table in ("clean_conversations", "relevant_conversations", "quarantine"):
            self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()

    # ---- runs ----
    def start_run(self, run_id: str) -> None:
        from datetime import datetime, timezone

        self.conn.execute(
            "INSERT OR REPLACE INTO funnel_runs (run_id, started_at, status) VALUES (?,?,?)",
            (run_id, datetime.now(timezone.utc).isoformat(), "running"),
        )
        self.conn.commit()

    def finish_run(self, run_id: str, per_source: dict[str, Any], summary: str) -> None:
        from datetime import datetime, timezone

        self.conn.execute(
            "UPDATE funnel_runs SET finished_at=?, status=?, per_source=?, summary=? WHERE run_id=?",
            (datetime.now(timezone.utc).isoformat(), "finished", json.dumps(per_source, default=str), summary, run_id),
        )
        self.conn.commit()

    # ---- readers ----
    def iter_clean(self) -> Any:
        for row in self.conn.execute("SELECT * FROM clean_conversations"):
            yield dict(row)

    def iter_relevant(self) -> Any:
        for row in self.conn.execute("SELECT * FROM relevant_conversations"):
            yield dict(row)

    def count_clean(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS n FROM clean_conversations").fetchone()["n"]

    def count_relevant(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS n FROM relevant_conversations").fetchone()["n"]

    def count_quarantine(self, tag: str | None = None) -> int:
        if tag:
            return self.conn.execute(
                "SELECT COUNT(*) AS n FROM quarantine WHERE quarantine_tag=?", (tag,)
            ).fetchone()["n"]
        return self.conn.execute("SELECT COUNT(*) AS n FROM quarantine").fetchone()["n"]

    def close(self) -> None:
        self.conn.close()