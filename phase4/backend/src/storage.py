"""Phase 4 storage — SQLite mirror + JSONL evidence packets + run bookkeeping."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_packets (
    packet_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    source TEXT,
    source_url TEXT,
    quote TEXT NOT NULL,
    quote_char_start INTEGER,
    quote_char_end INTEGER,
    intent TEXT,
    behaviours TEXT,
    barriers TEXT,
    unmet_needs TEXT,
    user_role TEXT,
    funnel_stage TEXT,
    segment_hints TEXT,
    confidence TEXT,
    extractor_version TEXT,
    three_level_said TEXT,
    three_level_inferred TEXT,
    three_level_concluded TEXT,
    UNIQUE(conversation_id)
);
CREATE TABLE IF NOT EXISTS extraction_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT, finished_at TEXT, status TEXT,
    per_source TEXT, summary TEXT
);
"""


class Storage:
    def __init__(self, out_dir: Path, db_path: Path | None = None):
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (out_dir / "phase4.sqlite3")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self.packets_jsonl = out_dir / "evidence_packets.jsonl"

    def save_packet(self, pkt: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO evidence_packets
               (packet_id, conversation_id, source, source_url, quote,
                quote_char_start, quote_char_end, intent, behaviours, barriers,
                unmet_needs, user_role, funnel_stage, segment_hints, confidence,
                extractor_version, three_level_said, three_level_inferred, three_level_concluded)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pkt["packet_id"], pkt["conversation_id"], pkt["source"], pkt["source_url"],
             pkt["quote"], pkt["quote_char_start"], pkt["quote_char_end"], pkt["intent"],
             json.dumps(pkt["behaviours"]), json.dumps(pkt["barriers"]),
             json.dumps(pkt["unmet_needs"]), pkt["user_role"], pkt["funnel_stage"],
             json.dumps(pkt["segment_hints"]), json.dumps(pkt["confidence"]),
             pkt["extractor_version"], pkt["three_level"]["said"],
             pkt["three_level"]["inferred"], pkt["three_level"]["concluded"]),
        )
        self.conn.commit()
        with open(self.packets_jsonl, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(pkt, ensure_ascii=False, default=str) + "\n")

    def reset(self) -> None:
        if self.packets_jsonl.exists():
            self.packets_jsonl.unlink()
        self.conn.execute("DELETE FROM evidence_packets")
        self.conn.commit()

    def start_run(self, run_id: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO extraction_runs (run_id, started_at, status) VALUES (?,?,?)",
            (run_id, datetime.now(timezone.utc).isoformat(), "running"),
        )
        self.conn.commit()

    def finish_run(self, run_id: str, per_source: dict[str, Any], summary: str) -> None:
        self.conn.execute(
            "UPDATE extraction_runs SET finished_at=?, status=?, per_source=?, summary=? WHERE run_id=?",
            (datetime.now(timezone.utc).isoformat(), "finished",
             json.dumps(per_source, default=str), summary, run_id),
        )
        self.conn.commit()

    def count_packets(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS n FROM evidence_packets").fetchone()["n"]

    def iter_packets(self):
        for row in self.conn.execute("SELECT * FROM evidence_packets"):
            yield dict(row)

    def close(self) -> None:
        self.conn.close()
