"""Storage: versioned JSONL output + SQLite mirror with dedup support."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .raw import now_iso, stable_id

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id           TEXT PRIMARY KEY,
    source       TEXT NOT NULL,
    source_external_id TEXT NOT NULL,
    url          TEXT NOT NULL,
    author       TEXT,
    timestamp    TEXT,
    text         TEXT NOT NULL,
    language     TEXT,
    engagement_metrics TEXT,
    collected_at TEXT NOT NULL,
    raw_hash     TEXT NOT NULL,
    is_duplicate_of TEXT,
    UNIQUE(source, source_external_id)
);
CREATE INDEX IF NOT EXISTS idx_conversations_hash ON conversations(raw_hash);
CREATE INDEX IF NOT EXISTS idx_conversations_source ON conversations(source);
CREATE INDEX IF NOT EXISTS idx_conversations_external ON conversations(source, source_external_id);

CREATE TABLE IF NOT EXISTS collection_runs (
    run_id       TEXT PRIMARY KEY,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    status       TEXT NOT NULL,
    per_source   TEXT,
    summary      TEXT
);
"""


class Storage:
    """Handles JSONL snapshots + SQLite mirror and all dedup bookkeeping."""

    def __init__(self, raw_dir: Path, db_path: Path):
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    # ---- queries -------------------------------------------------------
    def already_collected(self, source: str, external_id: str) -> str | None:
        row = self.conn.execute(
            "SELECT id FROM conversations WHERE source=? AND source_external_id=?",
            (source, external_id),
        ).fetchone()
        return row["id"] if row else None

    def find_by_hash(self, raw_hash: str, exclude_id: str | None = None) -> str | None:
        if exclude_id:
            row = self.conn.execute(
                "SELECT id FROM conversations WHERE raw_hash=? AND id<>? LIMIT 1",
                (raw_hash, exclude_id),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT id FROM conversations WHERE raw_hash=? LIMIT 1", (raw_hash,)
            ).fetchone()
        return row["id"] if row else None

    def count(self, source: str | None = None) -> int:
        if source:
            return self.conn.execute(
                "SELECT COUNT(*) AS n FROM conversations WHERE source=?", (source,)
            ).fetchone()["n"]
        return self.conn.execute("SELECT COUNT(*) AS n FROM conversations").fetchone()["n"]

    def save_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Persist a record, resolving cross-run dedup. Returns the stored record."""
        txt = json.dumps(record["engagement_metrics"]) if record["engagement_metrics"] else "{}"
        self.conn.execute(
            """INSERT OR IGNORE INTO conversations
               (id, source, source_external_id, url, author, timestamp,
                text, language, engagement_metrics, collected_at, raw_hash, is_duplicate_of)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record["id"],
                record["source"],
                record["source_external_id"],
                record["url"],
                record["author"],
                record["timestamp"],
                record["text"],
                record["language"],
                txt,
                record["collected_at"],
                record["raw_hash"],
                record["is_duplicate_of"],
            ),
        )
        self.conn.commit()
        return record

    # ---- JSONL snapshots ---------------------------------------------
    def snapshot_path(self, source: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return self.raw_dir / f"{source}__{stamp}.jsonl"

    def append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ---- runs ---------------------------------------------------------
    def start_run(self, run_id: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO collection_runs (run_id, started_at, status) VALUES (?,?,?)",
            (run_id, now_iso(), "running"),
        )
        self.conn.commit()

    def finish_run(self, run_id: str, per_source: dict[str, dict[str, Any]], summary: str) -> None:
        self.conn.execute(
            "UPDATE collection_runs SET finished_at=?, status=?, per_source=?, summary=? WHERE run_id=?",
            (now_iso(), "finished", json.dumps(per_source, default=str), summary, run_id),
        )
        self.conn.commit()

    def iter_conversations(self, source: str | None = None) -> Iterator[dict[str, Any]]:
        sql = "SELECT * FROM conversations"
        params: tuple = ()
        if source:
            sql += " WHERE source=?"
            params = (source,)
        for row in self.conn.execute(sql, params):
            yield dict(row)

    def close(self) -> None:
        self.conn.close()