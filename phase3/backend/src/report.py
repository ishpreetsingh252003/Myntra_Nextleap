"""Phase 3 reports: filtering funnel report + classifier accuracy report."""
from __future__ import annotations

from datetime import datetime
from typing import Any

SRC_HEADER = "| Source | Collected | Quarantined | Cleaned | Dedup-kept | Relevant | Relevant % |"


def render_funnel_report(funnel: dict[str, Any]) -> str:
    per_source = funnel.get("per_source", {})
    lines = [
        "# Phase 3 Filtering Funnel Report",
        "",
        f"- **Generated:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Run:** {funnel.get('run_id')}",
        f"- **Classifier:** {funnel.get('classifier_version')} "
        f"({('LLM available' if funnel.get('llm_available') else 'rules only, offline')})",
        "",
        f"**Totals:** collected={funnel.get('collected')} -> cleaned={funnel.get('cleaned')} "
        f"-> dedup-kept={funnel.get('deduped')} -> relevant={funnel.get('relevant')}",
        "",
        "Exact duplicates removed:", str(funnel.get("exact_dups")),
        "Near duplicates removed:", str(funnel.get("near_dups")),
        "",
        "## Per-source funnel",
        "",
        SRC_HEADER,
        "|--------|-----------|-------------|--------|-----------|----------|-------------|",
    ]
    for source, t in sorted(per_source.items()):
        pct = f"{100 * t['relevant'] / t['collected']:.0f}%" if t["collected"] else "-"
        lines.append(
            f"| {source} | {t['collected']} | {t['quarantined']} | {t['cleaned']} | "
            f"{t['deduped']} | {t['relevant']} | {pct} |"
        )
    quarantined = funnel.get("quarantined") or {}
    lines += [
        "",
        "## Quarantine breakdown (never deleted silently, EC-06/13/14/04/07)",
        "",
        *[f"- `{tag}`: {n}" for tag, n in sorted(quarantined.items())],
    ]
    return "\n".join(lines) + "\n"


def render_accuracy_report(acc: dict[str, Any]) -> str:
    lines = [
        "# Phase 3 Relevance Classifier Accuracy",
        "",
        f"- **Generated:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Golden set size:** {acc.get('n')}",
        f"- **Agreement (exact label match):** {acc.get('agreement')} "
        f"({acc.get('correct')}/{acc.get('n')})",
        f"- **Classifier version:** {acc.get('classifier_version')}",
        "- **Decision source:** " + ("LLM" if acc.get("llm_available") else "rules (offline baseline)"),
        "",
        "Target from architecture §4 Phase 3: ≥ 85% agreement vs human labels "
        "(LLM as decision-maker). The numbers below are the deterministic rule "
        "baseline — LLM typically improves on it when enabled.",
        "",
        "| Class | Precision | Recall | F1 | n |",
        "|-------|-----------|--------|----|---|",
    ]
    for cls, m in acc.get("metrics", {}).items():
        lines.append(
            f"| {cls} | {m['precision']} | {m['recall']} | {m['f1']} | {m['n']} |"
        )
    cat_acc = acc.get("category_accuracy")
    lines += [
        "",
        f"Category accuracy (of {acc.get('category_evaluated', 0)} relevant golden items with a category): "
        f"{cat_acc if cat_acc is not None else 'n/a'}",
        "",
        "## Predictions vs gold",
        "",
        "| id | gold | gold_cat | pred | pred_cat | conf | ok |",
        "|----|------|----------|------|----------|------|----|",
    ]
    for p in acc.get("predictions", []):
        lines.append(
            f"| {p['id']} | {p['gold_label']} | {p.get('gold_category') or '-'} | "
            f"{'relevant' if p['pred_relevant'] else 'not_relevant'} | {p['pred_category']} | "
            f"{p['confidence']} | {'YES' if p['correct'] else 'no'} |"
        )
    return "\n".join(lines) + "\n"