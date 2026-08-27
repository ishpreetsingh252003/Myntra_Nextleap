"""One-command orchestrator: runs the full Discovery Engine pipeline.

    python scripts/orchestrate.py --sources google_play app_store reddit \
        --from-date 2026-01-01 --to-date 2026-08-19 --live

    python scripts/orchestrate.py --fixtures          # offline demo, all 9 sources

Pipeline: Phase2 (scrape) -> Phase3 (clean+classify) -> Phase4 (extract)
          -> Phase5 (segment+cluster) -> Phase6 (score+report)

Each phase runs as its own subprocess (`python -m src.cli ...`) so their `src`
packages never collide, and phase outputs are chained through the shared
`app/data/` corpus. Flags flow down; LLM (Groq/Gemini) auto-enables when the
key is present in the phase .env files.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

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

RAW_CORPUS = DATA / "raw_corpus.jsonl"
RELEVANT = DATA / "relevant_corpus.jsonl"
PACKETS = DATA / "evidence_packets.jsonl"
REPORT = DATA / "discovery_report.md"


def run_phase(cwd: Path, args: list[str]) -> None:
    """Run a phase CLI as a subprocess, streaming output."""
    proc = subprocess.run([sys.executable, "-m", "src.cli", *args], cwd=str(cwd))
    if proc.returncode != 0:
        print(f"[orchestrate] phase failed in {cwd} with args {args}", file=sys.stderr)
        sys.exit(proc.returncode)


def write_jsonl(path: Path, records: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="orchestrate", description="Run the full Discovery Engine pipeline")
    parser.add_argument("--sources", nargs="+", help="live sources: google_play app_store reddit youtube_comments quora")
    parser.add_argument("--fixtures", action="store_true", help="offline demo using all 9 fixture sources")
    parser.add_argument("--from-date", dest="from_date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--to-date", dest="to_date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--skip-score", action="store_true", help="stop after Phase5")
    args = parser.parse_args(argv)

    if not args.fixtures and not args.sources:
        print("error: provide --sources (live) or --fixtures", file=sys.stderr)
        return 2
    if args.fixtures and args.sources:
        print("error: choose --fixtures OR --sources, not both", file=sys.stderr)
        return 2

    DATA.mkdir(parents=True, exist_ok=True)

    # ---- Phase 2: scrape (this must run in-process to reuse the adapter pkg) ----
    sys.path.insert(0, str(P2))
    from src.orchestrator import Orchestrator
    from src.storage import Storage as P2Storage
    import src.config as p2_config
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    storage = P2Storage(RAW_DIR, DATA / "corpus.sqlite3")
    orch = Orchestrator(storage)
    if args.fixtures:
        orch.collect_fixtures(from_date=args.from_date, to_date=args.to_date)
    else:
        plan = p2_config.load_plan()
        calls = [c for c in plan.adapter_calls
                 if c[0] in args.sources or c[1].get("source_name", c[0]) in args.sources]
        if not calls:
            print(f"error: no configured live sources match {args.sources}", file=sys.stderr)
            sys.path.pop(0)
            return 2
        for _, cfg in calls:
            if args.from_date:
                cfg["from_date"] = args.from_date
            if args.to_date:
                cfg["to_date"] = args.to_date
        orch.collect(calls, run_label="live")
    sys.path.pop(0)

    conn = sqlite3.connect(str(DATA / "corpus.sqlite3"))
    conn.row_factory = sqlite3.Row
    raw_records = [dict(r) for r in conn.execute("SELECT * FROM conversations")]
    conn.close()
    print(f"[orchestrate] Phase2 scrape: {len(raw_records)} raw records")
    write_jsonl(RAW_CORPUS, raw_records)

    # ---- Phase 3: clean + classify ----
    run_phase(P3, ["run", "--input", str(RAW_CORPUS), "--out", str(OUT3)])
    relevant_records = []
    rp = OUT3 / "relevant_corpus.jsonl"
    if rp.exists():
        relevant_records = [json.loads(l) for l in rp.read_text(encoding="utf-8").splitlines() if l.strip()]
    write_jsonl(RELEVANT, relevant_records)
    print(f"[orchestrate] Phase3 relevant: {len(relevant_records)}")

    # ---- Phase 4: extract ----
    run_phase(P4, ["run", "--input", str(RELEVANT), "--out", str(OUT4)])
    packets = []
    pp = OUT4 / "evidence_packets.jsonl"
    if pp.exists():
        packets = [json.loads(l) for l in pp.read_text(encoding="utf-8").splitlines() if l.strip()]
    write_jsonl(PACKETS, packets)
    print(f"[orchestrate] Phase4 evidence packets: {len(packets)}")

    # ---- Phase 5: segment + cluster ----
    run_phase(P5, ["run", "--input", str(PACKETS), "--out", str(OUT5)])

    if args.skip_score:
        print("\n[orchestrate] Stopping after Phase5 (--skip-score)")
        return 0

    # ---- Phase 6: score + report ----
    run_phase(P6, ["run", "--packets", str(PACKETS),
                   "--quant", str(OUT5 / "quantification.json"), "--out", str(OUT6)])

    print("\n[orchestrate] ALL PHASES COMPLETE")
    print(f"  raw corpus:    {RAW_CORPUS}")
    print(f"  relevant:      {RELEVANT}")
    print(f"  evidence:      {PACKETS}")
    print(f"  discovery:     {OUT6 / 'discovery_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
