"""Phase 5 reports — segmentation summary, theme clusters, quantification tables."""
from __future__ import annotations

from datetime import datetime
from typing import Any


def render_summary_report(stats: dict[str, Any]) -> str:
    quant = stats.get("quantification", {})
    lines = [
        "# Phase 5 Segmentation & Clustering Summary",
        "",
        f"- **Run:** {stats.get('run_id')}",
        f"- **Packets analysed:** {stats.get('total_packets')}",
        f"- **Themes (clusters):** {stats.get('clusters')}",
        f"- **Silhouette score:** {stats.get('silhouette')}",
        f"- **Extractor version:** {stats.get('extractor_version')}",
        "",
        "## Theme labels",
        "",
    ]
    for cid, label in stats.get("cluster_labels", {}).items():
        lines.append(f"- Cluster {cid}: **{label}**")

    lines += [
        "",
        "## Top behaviours",
        "",
        "| Behaviour | Count | % |",
        "|-----------|-------|---|",
    ]
    for item in quant.get("behaviours", []):
        lines.append(f"| {item['label']} | {item['count']} | {item['pct']}% |")

    lines += [
        "",
        "## Top barriers",
        "",
        "| Barrier | Count | % |",
        "|---------|-------|---|",
    ]
    for item in quant.get("barriers", []):
        lines.append(f"| {item['label']} | {item['count']} | {item['pct']}% |")

    lines += [
        "",
        "## Segments",
        "",
        "| Segment | Count | % |",
        "|---------|-------|---|",
    ]
    for item in quant.get("segments", []):
        lines.append(f"| {item['label']} | {item['count']} | {item['pct']}% |")

    lines += [
        "",
        "## Sources",
        "",
        "| Source | Count | % |",
        "|--------|-------|---|",
    ]
    for item in quant.get("sources", []):
        lines.append(f"| {item['label']} | {item['count']} | {item['pct']}% |")

    return "\n".join(lines) + "\n"
