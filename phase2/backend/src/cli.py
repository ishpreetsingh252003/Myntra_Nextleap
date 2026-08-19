"""Phase 2 CLI: collect conversations and render a run report.

Examples:
    python -m src.cli collect --fixtures
    python -m src.cli collect --fixtures --sources reddit_web csv_import
    python -m src.cli collect --live --sources google_play reddit app_store
    python -m src.cli report
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .storage import Storage
from .orchestrator import Orchestrator
from .report import render_adapter_log, render_report

DATA_DIR = Path(__file__).parents[2] / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "db" / "corpus.sqlite3"
REPORT_DIR = DATA_DIR / "reports"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phase2-collect", description="Collection layer for the Discovery Engine")
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="run the collection pipeline")
    collect.add_argument("--fixtures", action="store_true", help="offline mode using bundled sample data")
    collect.add_argument("--live", action="store_true", help="live mode (requires credentials/network)")
    collect.add_argument("--sources", nargs="+", help="sources to collect (default: all enabled)")
    collect.add_argument("--out", type=Path, default=None, help="override output dir")

    sub.add_parser("report", help="render the latest collection report from the DB")

    args = parser.parse_args(argv)
    raw_dir = (args.out / "raw") if args.out else RAW_DIR
    db_path = (args.out / "db" / "corpus.sqlite3") if args.out else DB_PATH

    if args.command == "collect":
        storage = Storage(raw_dir, db_path)
        orch = Orchestrator(storage)
        if args.fixtures:
            stats = orch.collect_fixtures(sources=args.sources)
            mode = "offline fixtures"
        elif args.live:
            if not args.sources:
                print("error: --live requires --sources (google_play app_store reddit)", file=sys.stderr)
                return 2
            calls = [("web_json" if s == "reddit_web" else s, {}) for s in args.sources]
            stats = orch.collect(calls, run_label="live")
            mode = "live"
        else:
            print("error: choose --fixtures or --live", file=sys.stderr)
            return 2

        report = render_report(db_path, stats, mode)
        report_dir = (args.out / "reports") if args.out else REPORT_DIR
        report_dir.mkdir(parents=True, exist_ok=True)
        latest = report_dir / "latest.md"
        latest.write_text(report, encoding="utf-8")
        (report_dir / "latest_adapter_log.md").write_text(
            render_adapter_log(orch.adapter_log) + "\n", encoding="utf-8"
        )
        print(report)
        print("\nAdapter log:\n" + "".join(f"- {l}\n" for l in orch.adapter_log))
        print(f"\nReport written to {latest}")
        return 0

    if args.command == "report":
        report = render_report(db_path, {}, "report-only")
        print(report)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())