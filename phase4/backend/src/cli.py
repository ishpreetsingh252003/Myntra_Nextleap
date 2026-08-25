"""Phase 4 CLI.

Examples:
    python -m src.cli run --input ../phase3/data/output/relevant_corpus.jsonl
    python -m src.cli run --input ../phase3/data/output/relevant_corpus.jsonl --out output
    python -m src.cli accuracy --golden ../data/golden_set/evidence_golden.jsonl
    python -m src.cli report --out output
    python -m src.cli sample --out output
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator

from .config import load_config
from .evidence import EvidencePacketBuilder
from .evaluator import Evaluator, read_golden
from .llm import LLMExtractor
from .pipeline import Pipeline
from .report import render_accuracy_report, render_sample_packets, render_summary_report
from .storage import Storage

P4 = Path(__file__).resolve().parents[2]
DATA_DIR = P4 / "data"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phase4-extract", description="Behaviour/Barrier/Unmet-Need extraction")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run extraction pipeline on relevant corpus")
    run.add_argument("--input", type=Path, default=P4.parent / "phase3" / "data" / "output" / "relevant_corpus.jsonl")
    run.add_argument("--out", type=Path, default=None)

    acc = sub.add_parser("accuracy", help="extraction accuracy vs golden set")
    acc.add_argument("--out", type=Path, default=None)

    sub.add_parser("report", help="render extraction summary from latest run").add_argument("--out", type=Path, default=None)

    sample = sub.add_parser("sample", help="show sample evidence packets")
    sample.add_argument("--out", type=Path, default=None)
    sample.add_argument("--n", type=int, default=5)

    args = parser.parse_args(argv)
    cfg = load_config()
    out_dir = args.out.resolve() if args.out else (DATA_DIR / "output").resolve()

    if args.command == "run":
        storage = Storage(out_dir)
        pipeline = Pipeline(storage, cfg)
        stats = pipeline.run(read_jsonl(args.input))
        (out_dir / "extraction_summary.md").write_text(render_summary_report(stats), encoding="utf-8")
        print(render_summary_report(stats))
        print(f"\nOutputs in {out_dir}")
        return 0

    if args.command == "accuracy":
        golden_path = DATA_DIR / "golden_set" / "evidence_golden.jsonl"
        if not golden_path.exists():
            print("error: golden set not found", file=sys.stderr)
            return 2
        builder = EvidencePacketBuilder(cfg)
        golden = list(read_golden(golden_path))
        rule_extractions = []
        for g in golden:
            from .barrier import RuleBarrierExtractor
            from .behaviour import RuleBehaviourExtractor
            from .unmet_needs import UnmetNeedInferrer
            text = g.get("source_text", "")
            beh = RuleBehaviourExtractor(cfg).extract(text)
            bar = RuleBarrierExtractor(cfg).extract(text)
            needs = UnmetNeedInferrer(cfg).infer(text, bar["barriers"])
            rule_extractions.append({**beh, **bar, "unmet_needs": needs, "confidence": {}})
        acc_result = Evaluator(builder).evaluate(golden, rule_extractions)
        acc_result["llm_available"] = LLMExtractor(cfg).available()
        (out_dir / "extraction_accuracy.md").write_text(render_accuracy_report(acc_result), encoding="utf-8")
        print(render_accuracy_report(acc_result))
        return 0

    if args.command == "report":
        storage = Storage(out_dir)
        print(f"Evidence packets: {storage.count_packets()}")
        return 0

    if args.command == "sample":
        storage = Storage(out_dir)
        packets = list(storage.iter_packets())
        if not packets:
            print("no packets found; run extraction first")
            return 1
        print(render_sample_packets(packets, n=getattr(args, "n", 5)))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
