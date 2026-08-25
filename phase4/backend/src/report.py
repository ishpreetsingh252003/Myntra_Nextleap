"""Phase 4 reports: extraction accuracy report + sample evidence packets."""
from __future__ import annotations

from datetime import datetime
from typing import Any


def render_accuracy_report(acc: dict[str, Any]) -> str:
    lines = [
        "# Phase 4 Extraction Accuracy Report",
        "",
        f"- **Generated:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Golden set size:** {acc.get('n')}",
        f"- **Extractor version:** {acc.get('extractor_version')}",
        "- **Decision source:** " + ("LLM" if acc.get("llm_available") else "rules (offline baseline)"),
        "",
        "Architecture target: ≥ 80% agreement vs human labels.",
        "",
        "## Extraction quality",
        "",
        "| Metric | Score |",
        "|--------|-------|",
        f"| Behaviour F1 (avg) | {acc.get('behaviour_f1')} |",
        f"| Barrier F1 (avg) | {acc.get('barrier_f1')} |",
        f"| **Overall agreement** | **{acc.get('overall_agreement')}** |",
        f"| Three-level pass rate | {acc.get('three_level_pass_rate')} |",
        f"| Quote valid rate | {acc.get('quote_valid_rate')} |",
        f"| Intent accuracy | {acc.get('intent_accuracy')} |",
        "",
        "## Per-packet breakdown",
        "",
        "| id | gold_beh | pred_beh | beh_f1 | gold_bar | pred_bar | bar_f1 | 3L | quote | intent |",
        "|----|----------|----------|--------|----------|----------|--------|-----|-------|--------|",
    ]
    for p in acc.get("predictions", []):
        gb = ",".join(p["gold_behaviours"][:3]) or "-"
        pb = ",".join(p["pred_behaviours"][:3]) or "-"
        gbar = ",".join(p["gold_barriers"][:3]) or "-"
        pbar = ",".join(p["pred_barriers"][:3]) or "-"
        lines.append(
            f"| {p['id']} | {gb} | {pb} | {p['beh_f1']} | {gbar} | {pbar} | {p['bar_f1']} "
            f"| {'ok' if p['three_level_ok'] else 'MISS'} "
            f"| {'ok' if p['quote_ok'] else 'MISS'} "
            f"| {'ok' if p['intent_ok'] else 'MISS'} |"
        )
    return "\n".join(lines) + "\n"


def render_summary_report(stats: dict[str, Any]) -> str:
    lines = [
        "# Phase 4 Extraction Run Summary",
        "",
        f"- **Run:** {stats.get('run_id')}",
        f"- **Input:** {stats.get('total_input')} conversations",
        f"- **Extracted:** {stats.get('extracted')} evidence packets",
        f"- **LLM used:** {stats.get('llm_used')} packets",
        f"- **Offset mismatches:** {stats.get('offset_mismatches')}",
        f"- **Extractor version:** {stats.get('extractor_version')}",
        f"- **Embedding dim:** {stats.get('embedding_dim')}",
        "",
        "## Per-source",
        "",
        "| Source | Input | Extracted | LLM |",
        "|--------|-------|-----------|-----|",
    ]
    for source, t in sorted(stats.get("per_source", {}).items()):
        lines.append(f"| {source} | {t['input']} | {t['extracted']} | {t['llm']} |")
    return "\n".join(lines) + "\n"


def render_sample_packets(packets: list[dict[str, Any]], n: int = 5) -> str:
    lines = [
        "# Phase 4 Sample Evidence Packets",
        "",
        f"Showing {min(n, len(packets))} of {len(packets)} packets.",
        "",
    ]
    for pkt in packets[:n]:
        three_level = pkt.get("three_level") or {
            "said": pkt.get("three_level_said", ""),
            "inferred": pkt.get("three_level_inferred", ""),
            "concluded": pkt.get("three_level_concluded", ""),
        }
        lines += [
            f"## {pkt['packet_id']} (conv: {pkt['conversation_id']})",
            "",
            f"**Source:** {pkt['source']} · **URL:** {pkt['source_url']}",
            f"**Intent:** {pkt['intent']} · **Funnel:** {pkt['funnel_stage']} · **Role:** {pkt['user_role']}",
            "",
            f"> {pkt['quote']}",
            "",
            f"**Behaviours:** {', '.join(pkt['behaviours']) if isinstance(pkt['behaviours'], list) else pkt['behaviours'] or 'none'}",
            f"**Barriers:** {', '.join(pkt['barriers']) if isinstance(pkt['barriers'], list) else pkt['barriers'] or 'none'}",
            f"**Unmet needs:** {', '.join(pkt['unmet_needs']) if isinstance(pkt['unmet_needs'], list) else pkt['unmet_needs'] or 'none'}",
            f"**Segment hints:** {', '.join(pkt['segment_hints']) if isinstance(pkt['segment_hints'], list) else pkt['segment_hints'] or 'none'}",
            "",
            "### Three-level distinction",
            "",
            f"- **Said:** {three_level['said']}",
            f"- **Inferred:** {three_level['inferred']}",
            f"- **Concluded:** {three_level['concluded']}",
            "",
            "---",
            "",
        ]
    return "\n".join(lines) + "\n"
