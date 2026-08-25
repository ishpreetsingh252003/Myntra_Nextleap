"""Phase 6 CLI.

Examples:
    python -m src.cli run --packets ../phase4/data/output/evidence_packets.jsonl --quant ../phase5/data/output/quantification.json
    python -m src.cli report --out output
    python -m src.cli opportunities --out output
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator

from .config import load_config
from .evidence_db import EvidenceDB
from .pipeline import Pipeline
from .report import render_discovery_report
from .storage import Storage

P6 = Path(__file__).resolve().parents[2]
DATA_DIR = P6 / "data"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phase6-opportunity", description="Opportunity ranking & Discovery Report")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument("--packets", type=Path, default=P6.parent / "phase4" / "data" / "output" / "evidence_packets.jsonl")
    run.add_argument("--quant", type=Path, default=P6.parent / "phase5" / "data" / "output" / "quantification.json")
    run.add_argument("--out", type=Path, default=None)

    report = sub.add_parser("report")
    report.add_argument("--out", type=Path, default=None)

    opps = sub.add_parser("opportunities")
    opps.add_argument("--out", type=Path, default=None)

    args = parser.parse_args(argv)
    cfg = load_config()
    out_dir = args.out.resolve() if args.out else (DATA_DIR / "output").resolve()

    if args.command == "run":
        storage = Storage(out_dir)
        evidence_db = EvidenceDB(out_dir / "evidence.db")
        pipeline = Pipeline(storage, evidence_db, cfg)

        quant = {}
        if args.quant.exists():
            quant = json.loads(args.quant.read_text(encoding="utf-8"))

        stats = pipeline.run(read_jsonl(args.packets), quant)
        evidence_db.close()
        print(f"Run: {stats['run_id']}")
        print(f"Opportunities: {stats['opportunities']}")
        print(f"Report: {stats['report_path']}")
        return 0

    if args.command == "report":
        db_path = out_dir / "evidence.db"
        if not db_path.exists():
            print("error: run pipeline first", file=sys.stderr)
            return 2
        edb = EvidenceDB(db_path)
        opps = edb.get_opportunities()
        edb.close()
        print(f"Opportunities: {len(opps)}")
        for o in opps:
            print(f"  #{o['rank']} {o['title']} (score: {o['score']})")
        return 0

    if args.command == "opportunities":
        storage = Storage(out_dir)
        for opp in storage.iter_opportunities():
            print(f"#{opp['rank']} {opp['title']} (score: {opp['score']})")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
