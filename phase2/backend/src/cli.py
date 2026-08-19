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
    collect.add_argument("--from-date", dest="from_date", default=None, help="ISO start date (YYYY-MM-DD); keeps records on/after (live + fixtures)")
    collect.add_argument("--to-date", dest="to_date", default=None, help="ISO end date (YYYY-MM-DD); keeps records on/before")
    collect.add_argument("--out", type=Path, default=None, help="override output dir")

    sub.add_parser("report", help="render the latest collection report from the DB")

    args = parser.parse_args(argv)
    raw_dir = (args.out / "raw") if args.out else RAW_DIR
    db_path = (args.out / "db" / "corpus.sqlite3") if args.out else DB_PATH

    if args.command == "collect":
        storage = Storage(raw_dir, db_path)
        orch = Orchestrator(storage)
        if args.fixtures:
            stats = orch.collect_fixtures(sources=args.sources, from_date=args.from_date, to_date=args.to_date)
            mode = "offline fixtures"
        elif args.live:
            from .config import load_plan

            plan = load_plan()
            if args.sources:
                calls = [c for c in plan.adapter_calls if c[0] in args.sources or c[1].get("source_name") in args.sources]
            else:
                calls = plan.adapter_calls
            if not calls:
                print("error: no configured sources match the requested --sources", file=sys.stderr)
                return 2
            for _, cfg in calls:
                if args.from_date:
                    cfg["from_date"] = args.from_date
                if args.to_date:
                    cfg["to_date"] = args.to_date
            stats = orch.collect(calls, run_label="live")
            mode = "live"
        else:
            print("error: choose --fixtures or --live", file=sys.stderr)
            return 2

        report = render_report(db_path, stats, mode, only_ids=orch.last_run_ids if args.command == "collect" else None)
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