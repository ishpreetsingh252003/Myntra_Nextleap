"""Phase 3 CLI.

Examples:
    python -m src.cli run --input ../data/fixtures/raw_sample.jsonl
    python -m src.cli run --input ../phase2/data/raw/0000.jsonl --out output
    python -m src.cli accuracy --golden ../data/golden_set/relevance_golden.jsonl
    python -m src.cli report --out output
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator

from .config import load_config
from .evaluator import Evaluator, read_golden
from .pipeline import Pipeline
from .report import render_accuracy_report, render_funnel_report
from .storage import Storage

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR.parent / "data"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phase3-clean", description="Cleaning + relevance layer")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run cleaning->dedup->relevance pipeline")
    run.add_argument("--input", type=Path, default=DATA_DIR / "fixtures" / "raw_sample.jsonl",
                     help="raw corpus JSONL (one record per line)")
    run.add_argument("--out", type=Path, default=None, help="output dir (default data/output)")

    acc_parser = sub.add_parser("accuracy", help="relevance classifier accuracy vs golden set")
    acc_parser.add_argument("--out", type=Path, default=None, help="output dir")

    report = sub.add_parser("report", help="render funnel/accuracy reports from latest run")
    report.add_argument("--out", type=Path, default=None, help="output dir")

    args = parser.parse_args(argv)
    cfg = load_config()
    out_dir = args.out.resolve() if args.out else (DATA_DIR / "output").resolve()

    if args.command == "run":
        storage = Storage(out_dir)
        pipeline = Pipeline(storage, cfg)
        stats = pipeline.run(read_jsonl(args.input))
        (out_dir / "funnel_report.md").write_text(render_funnel_report(stats), encoding="utf-8")
        print(render_funnel_report(stats))
        print(f"\nOutputs in {out_dir}")
        return 0

    if args.command == "accuracy":
        golden_path = Path(BACKEND_DIR) / ".." / "data" / "golden_set" / "relevance_golden.jsonl"
        if not golden_path.exists():
            print("error: golden set not found", file=sys.stderr)
            return 2
        from .relevance import RelevanceClassifier

        acc = Evaluator(RelevanceClassifier(cfg)).evaluate(list(read_golden(golden_path)))
        (out_dir / "accuracy_report.md").write_text(render_accuracy_report(acc), encoding="utf-8")
        print(render_accuracy_report(acc))
        return 0

    if args.command == "report":
        storage = Storage(out_dir)
        print(f"Clean corpus rows: {storage.count_clean()}")
        print(f"Relevant corpus rows: {storage.count_relevant()}")
        print(f"Quarantined rows: {storage.count_quarantine()}")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())