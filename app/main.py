"""FastAPI backend for the Discovery Engine — deployable on Render.

Endpoints:
    POST /api/scrape          Run live (or fixture) scraping for sources + date range.
    POST /api/analyze         Run the full pipeline (clean->extract->segment->score).
    POST /api/run             One-shot: scrape + analyze in a single call.
    GET  /api/results         Latest evidence packets + opportunities + report.
    GET  /api/opportunities   Ranked opportunities from the evidence DB.
    GET  /api/health          Live-check for Render.

Requires dependencies in app/requirements.txt. Set env vars (GROQ_API_KEY etc.)
in the Render dashboard; source creds (REDDIT/YouTube) under phase2/backend/.env.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
P2 = ROOT / "phase2" / "backend"
P3 = ROOT / "phase3" / "backend"
P4 = ROOT / "phase4" / "backend"
P5 = ROOT / "phase5" / "backend"
P6 = ROOT / "phase6" / "backend"

DATA = ROOT / "app" / "data"
RAW_DIR = DATA / "raw"
OUT3 = DATA / "output" / "phase3"
OUT4 = DATA / "output" / "phase4"
OUT5 = DATA / "output" / "phase5"
OUT6 = DATA / "output" / "phase6"

REPORT = OUT6 / "discovery_report.md"

# prevent -m src.cli subprocess name collisions across phases
for p in (P2, P3, P4, P5, P6):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

app = FastAPI(title="Myntra Wishlist Discovery Engine", version="1.0.0")


# ---- request/response models ----------------------------------------------
class ScrapeRequest(BaseModel):
    sources: list[str]
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class AnalyzeRequest(BaseModel):
    pass


class RunRequest(BaseModel):
    sources: list[str]
    from_date: Optional[str] = None
    to_date: Optional[str] = None


# ---- pipeline execution helpers -------------------------------------------
def _run_phase(cwd: Path, args: list[str]) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "src.cli", *args],
        cwd=str(cwd), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"phase '{cwd.name}' failed: {proc.stderr[-1500:]}")
    return proc.stdout


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def _scrape_impl(sources: list[str], from_date: str | None, to_date: str | None) -> dict:
    # Phase 2 must run in-process to reuse the adapter package.
    sys.path.insert(0, str(P2))
    try:
        from src.orchestrator import Orchestrator
        from src.storage import Storage as P2Storage
        import src.config as p2_config
    finally:
        # keep P2 importable for subsequent steps without polluting later phases
        pass

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    storage = P2Storage(RAW_DIR, DATA / "corpus.sqlite3")
    orch = Orchestrator(storage)
    plan = p2_config.load_plan()
    calls = [c for c in plan.adapter_calls
             if c[0] in sources or c[1].get("source_name", c[0]) in sources]
    if not calls:
        raise HTTPException(status_code=400, detail=f"No configured source matched {sources}")
    for _, cfg in calls:
        if from_date:
            cfg["from_date"] = from_date
        if to_date:
            cfg["to_date"] = to_date
    orch.collect(calls, run_label="live")

    conn = sqlite3.connect(str(DATA / "corpus.sqlite3"))
    conn.row_factory = sqlite3.Row
    raw = [dict(r) for r in conn.execute("SELECT * FROM conversations")]
    conn.close()
    _write_jsonl(DATA / "raw_corpus.jsonl", raw)
    return {"sources": sources, "raw_count": len(raw), "from_date": from_date, "to_date": to_date}


def _analyze_impl() -> dict:
    # Phase 3
    _run_phase(P3, ["run", "--input", str(DATA / "raw_corpus.jsonl"), "--out", str(OUT3)])
    rel = _read_jsonl(OUT3 / "relevant_corpus.jsonl")
    _write_jsonl(DATA / "relevant_corpus.jsonl", rel)
    # Phase 4
    _run_phase(P4, ["run", "--input", str(DATA / "relevant_corpus.jsonl"), "--out", str(OUT4)])
    pkts = _read_jsonl(OUT4 / "evidence_packets.jsonl")
    _write_jsonl(DATA / "evidence_packets.jsonl", pkts)
    # Phase 5
    _run_phase(P5, ["run", "--input", str(DATA / "evidence_packets.jsonl"), "--out", str(OUT5)])
    # Phase 6
    _run_phase(P6, ["run", "--packets", str(DATA / "evidence_packets.jsonl"),
                    "--quant", str(OUT5 / "quantification.json"), "--out", str(OUT6)])
    return {"relevant": len(rel), "evidence_packets": len(pkts), "report": str(REPORT)}


# ---- routes ---------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "data_dir": str(DATA)}


@app.post("/api/scrape")
def scrape(req: ScrapeRequest) -> dict:
    result = _scrape_impl(req.sources, req.from_date, req.to_date)
    return {"status": "ok", "result": result}


@app.post("/api/analyze")
def analyze(_: Optional[AnalyzeRequest] = None) -> dict:
    result = _analyze_impl()
    return {"status": "ok", "result": result}


@app.post("/api/run")
def run(req: RunRequest) -> dict:
    scrape_result = _scrape_impl(req.sources, req.from_date, req.to_date)
    analyze_result = _analyze_impl()
    return {"status": "ok", "scrape": scrape_result, "analyze": analyze_result}


@app.get("/api/results")
def results() -> dict:
    packets = _read_jsonl(DATA / "evidence_packets.jsonl")
    opportunities = []
    dbp = OUT6 / "evidence.db"
    if dbp.exists():
        conn = sqlite3.connect(str(dbp))
        conn.row_factory = sqlite3.Row
        opportunities = [dict(r) for r in conn.execute("SELECT * FROM opportunities ORDER BY rank")]
        conn.close()
    report = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    return {
        "evidence_packets": packets,
        "opportunities": opportunities,
        "report": report,
    }


@app.get("/api/opportunities")
def opportunities() -> list[dict[str, Any]]:
    dbp = OUT6 / "evidence.db"
    if not dbp.exists():
        raise HTTPException(status_code=404, detail="Run analyze first")
    conn = sqlite3.connect(str(dbp))
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM opportunities ORDER BY rank")]
    conn.close()
    return rows
