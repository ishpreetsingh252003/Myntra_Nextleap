"""Evidence Database — links opportunities → evidence packets → quotes → source URLs.

Every insight is traceable to raw data with confidence scores.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id TEXT PRIMARY KEY,
    rank INTEGER,
    title TEXT,
    score REAL,
    score_breakdown TEXT,
    behaviours TEXT,
    barriers TEXT,
    evidence_strength TEXT,
    interview_questions TEXT,
    supporting_packet_ids TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS evidence_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id TEXT,
    packet_id TEXT,
    conversation_id TEXT,
    source TEXT,
    source_url TEXT,
    quote TEXT,
    relevance REAL,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id)
);
"""


class EvidenceDB:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def save_opportunity(self, opp: dict[str, Any], packets: list[dict[str, Any]],
                         questions: list[str]) -> None:
        import json
        self.conn.execute(
            """INSERT OR REPLACE INTO opportunities
               (opportunity_id, rank, title, score, score_breakdown, behaviours,
                barriers, evidence_strength, interview_questions, supporting_packet_ids, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (f"OPP-{opp['rank']:03d}", opp["rank"], opp["title"], opp["score"],
             json.dumps(opp.get("breakdown", {})), json.dumps(opp.get("behaviours", [])),
             json.dumps(opp.get("barriers", [])), opp.get("evidence_strength", "medium"),
             json.dumps(questions), json.dumps([p.get("packet_id", "") for p in packets]),
             __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()),
        )
        for pkt in packets:
            self.conn.execute(
                """INSERT INTO evidence_links
                   (opportunity_id, packet_id, conversation_id, source, source_url, quote, relevance)
                   VALUES (?,?,?,?,?,?,?)""",
                (f"OPP-{opp['rank']:03d}", pkt.get("packet_id", ""), pkt.get("conversation_id", ""),
                 pkt.get("source", ""), pkt.get("source_url", ""), pkt.get("quote", ""), 1.0),
            )
        self.conn.commit()

    def get_opportunities(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM opportunities ORDER BY rank").fetchall()
        return [dict(r) for r in rows]

    def get_evidence_for_opportunity(self, opp_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM evidence_links WHERE opportunity_id=?", (opp_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def count_opportunities(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS n FROM opportunities").fetchone()["n"]

    def count_evidence_links(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS n FROM evidence_links").fetchone()["n"]

    def close(self) -> None:
        self.conn.close()
