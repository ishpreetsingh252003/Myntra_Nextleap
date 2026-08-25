"""Phase 6 storage — SQLite opportunity store + run bookkeeping."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS ranked_opportunities (
    opportunity_id TEXT PRIMARY KEY,
    rank INTEGER,
    title TEXT,
    score REAL,
    score_breakdown TEXT,
    behaviours TEXT,
    barriers TEXT,
    evidence_strength TEXT,
    interview_questions TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS phase6_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT, finished_at TEXT, status TEXT, summary TEXT
);
"""


class Storage:
    def __init__(self, out_dir: Path, db_path: Path | None = None):
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (out_dir / "phase6.sqlite3")
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def save_opportunity(self, opp: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO ranked_opportunities
               (opportunity_id, rank, title, score, score_breakdown, behaviours,
                barriers, evidence_strength, interview_questions, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (f"OPP-{opp['rank']:03d}", opp["rank"], opp["title"], opp["score"],
             json.dumps(opp.get("breakdown", {})), json.dumps(opp.get("behaviours", [])),
             json.dumps(opp.get("barriers", [])), opp.get("evidence_strength", "medium"),
             json.dumps(opp.get("interview_questions", [])),
             datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def start_run(self, run_id: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO phase6_runs (run_id, started_at, status) VALUES (?,?,?)",
            (run_id, datetime.now(timezone.utc).isoformat(), "running"),
        )
        self.conn.commit()

    def finish_run(self, run_id: str, data: dict[str, Any], summary: str) -> None:
        self.conn.execute(
            "UPDATE phase6_runs SET finished_at=?, status=?, summary=? WHERE run_id=?",
            (datetime.now(timezone.utc).isoformat(), "finished", summary, run_id),
        )
        self.conn.commit()

    def count_opportunities(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS n FROM ranked_opportunities").fetchone()["n"]

    def iter_opportunities(self):
        for row in self.conn.execute("SELECT * FROM ranked_opportunities ORDER BY rank"):
            yield dict(row)

    def close(self) -> None:
        self.conn.close()
