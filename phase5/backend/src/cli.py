"""Phase 5 CLI.

Examples:
    python -m src.cli run --input ../phase4/data/output/evidence_packets.jsonl
    python -m src.cli report --out output
    python -m src.cli validate --out output
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator

from .config import load_config
from .evaluator import validate
from .pipeline import Pipeline
from .report import render_summary_report
from .storage import Storage

P5 = Path(__file__).resolve().parents[2]
DATA_DIR = P5 / "data"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phase5-segment", description="Segmentation, clustering & quantification")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument("--input", type=Path, default=P5.parent / "phase4" / "data" / "output" / "evidence_packets.jsonl")
    run.add_argument("--out", type=Path, default=None)

    report = sub.add_parser("report")
    report.add_argument("--out", type=Path, default=None)

    val = sub.add_parser("validate")
    val.add_argument("--out", type=Path, default=None)

    args = parser.parse_args(argv)
    cfg = load_config()
    out_dir = args.out.resolve() if args.out else (DATA_DIR / "output").resolve()

    if args.command == "run":
        storage = Storage(out_dir)
        pipeline = Pipeline(storage, cfg)
        stats = pipeline.run(read_jsonl(args.input))
        (out_dir / "segmentation_report.md").write_text(render_summary_report(stats), encoding="utf-8")
        print(render_summary_report(stats))
        print(f"\nOutputs in {out_dir}")
        return 0

    if args.command == "report":
        storage = Storage(out_dir)
        print(f"Segmented packets: {storage.count_packets()}")
        return 0

    if args.command == "validate":
        quant_path = out_dir / "quantification.json"
        if not quant_path.exists():
            print("error: run segmentation first", file=sys.stderr)
            return 2
        quant = json.loads(quant_path.read_text(encoding="utf-8"))
        result = validate(quant)
        print(f"Pass: {result['pass']}")
        print(f"Segments: {result['n_segments']}, Themes: {result['n_themes']}")
        if result["issues"]:
            for issue in result["issues"]:
                print(f"  - {issue}")
        return 0 if result["pass"] else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
