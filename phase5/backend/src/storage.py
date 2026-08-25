"""Phase 5 storage — SQLite mirror + CSV quantification + run bookkeeping."""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS segmented_packets (
    packet_id TEXT PRIMARY KEY,
    conversation_id TEXT, source TEXT, quote TEXT,
    behaviours TEXT, barriers TEXT, unmet_needs TEXT,
    intent TEXT, funnel_stage TEXT, user_role TEXT,
    segment_hints TEXT, assigned_segments TEXT,
    cluster_id INTEGER, cluster_label TEXT,
    source_url TEXT, extractor_version TEXT
);
CREATE TABLE IF NOT EXISTS segmentation_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT, finished_at TEXT, status TEXT,
    summary TEXT
);
"""


class Storage:
    def __init__(self, out_dir: Path, db_path: Path | None = None):
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (out_dir / "phase5.sqlite3")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self.packets_jsonl = out_dir / "segmented_packets.jsonl"

    def save_packet(self, pkt: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO segmented_packets
               (packet_id, conversation_id, source, quote, behaviours, barriers,
                unmet_needs, intent, funnel_stage, user_role, segment_hints,
                assigned_segments, cluster_id, cluster_label, source_url, extractor_version)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pkt.get("packet_id", ""), pkt.get("conversation_id", ""), pkt.get("source", ""),
             pkt.get("quote", ""), json.dumps(pkt.get("behaviours", [])),
             json.dumps(pkt.get("barriers", [])), json.dumps(pkt.get("unmet_needs", [])),
             pkt.get("intent", ""), pkt.get("funnel_stage", ""), pkt.get("user_role", ""),
             json.dumps(pkt.get("segment_hints", [])), json.dumps(pkt.get("assigned_segments", [])),
             pkt.get("cluster_id", 0), pkt.get("cluster_label", ""),
             pkt.get("source_url", ""), pkt.get("extractor_version", "")),
        )
        self.conn.commit()
        with open(self.packets_jsonl, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(pkt, ensure_ascii=False, default=str) + "\n")

    def save_quantification(self, quant: dict[str, Any]) -> None:
        # save as CSV tables
        for key in ("behaviours", "barriers", "unmet_needs", "segments", "themes",
                     "intents", "funnel_stages", "sources"):
            data = quant.get(key, [])
            if data:
                path = self.out_dir / f"quant_{key}.csv"
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=["label", "count", "pct"])
                    writer.writeheader()
                    writer.writerows(data)
        # save co-occurrence matrix
        co = quant.get("co_occurrence", [])
        if co:
            path = self.out_dir / "quant_co_occurrence.csv"
            with open(path, "w", encoding="utf-8", newline="") as fh:
                if co:
                    writer = csv.DictWriter(fh, fieldnames=list(co[0].keys()))
                    writer.writeheader()
                    writer.writerows(co)
        # save full quantification as JSON
        (self.out_dir / "quantification.json").write_text(
            json.dumps(quant, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )

    def reset(self) -> None:
        for p in (self.packets_jsonl,):
            if p.exists():
                p.unlink()
        self.conn.execute("DELETE FROM segmented_packets")
        self.conn.commit()

    def start_run(self, run_id: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO segmentation_runs (run_id, started_at, status) VALUES (?,?,?)",
            (run_id, datetime.now(timezone.utc).isoformat(), "running"),
        )
        self.conn.commit()

    def finish_run(self, run_id: str, quant: dict[str, Any], summary: str) -> None:
        self.conn.execute(
            "UPDATE segmentation_runs SET finished_at=?, status=?, summary=? WHERE run_id=?",
            (datetime.now(timezone.utc).isoformat(), "finished", summary, run_id),
        )
        self.conn.commit()

    def count_packets(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS n FROM segmented_packets").fetchone()["n"]

    def iter_packets(self):
        for row in self.conn.execute("SELECT * FROM segmented_packets"):
            yield dict(row)

    def close(self) -> None:
        self.conn.close()
