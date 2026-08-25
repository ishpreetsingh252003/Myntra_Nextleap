"""Quantification — frequency tables, co-occurrence matrices, per-source/per-segment stats.

Clearly separates frequency of mention from evidence of business impact (§5.1).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def quantify(packets: list[dict[str, Any]], cluster_labels: list[int],
             cluster_names: dict[int, str]) -> dict[str, Any]:
    """Build quantification tables from labelled evidence packets."""
    n = len(packets)
    if n == 0:
        return {"total": 0}

    # ---- per-behaviour counts ----
    beh_counts: Counter = Counter()
    bar_counts: Counter = Counter()
    need_counts: Counter = Counter()
    intent_counts: Counter = Counter()
    funnel_counts: Counter = Counter()
    source_counts: Counter = Counter()
    segment_counts: Counter = Counter()
    cluster_counts: Counter = Counter()

    # ---- co-occurrence ----
    beh_bar_co: dict[str, Counter] = defaultdict(Counter)
    beh_beh_co: dict[str, Counter] = defaultdict(Counter)

    # ---- per-source breakdown ----
    source_beh: dict[str, Counter] = defaultdict(Counter)
    source_bar: dict[str, Counter] = defaultdict(Counter)

    # ---- per-segment breakdown ----
    seg_beh: dict[str, Counter] = defaultdict(Counter)
    seg_bar: dict[str, Counter] = defaultdict(Counter)

    for i, p in enumerate(packets):
        behs = p.get("behaviours", [])
        bars = p.get("barriers", [])
        needs = p.get("unmet_needs", [])
        segs = p.get("segment_hints", [])
        source = p.get("source", "unknown")
        cluster_id = cluster_labels[i] if i < len(cluster_labels) else 0

        for b in behs:
            beh_counts[b] += 1
            source_beh[source][b] += 1
            for s in segs:
                seg_beh[s][b] += 1
        for b in bars:
            bar_counts[b] += 1
            source_bar[source][b] += 1
            for s in segs:
                seg_bar[s][b] += 1
        for b in behs:
            for br in bars:
                beh_bar_co[b][br] += 1
        for i1 in range(len(behs)):
            for i2 in range(i1 + 1, len(behs)):
                beh_beh_co[behs[i1]][behs[i2]] += 1
                beh_beh_co[behs[i2]][behs[i1]] += 1
        for need in needs:
            need_counts[need] += 1
        intent_counts[p.get("intent", "unknown")] += 1
        funnel_counts[p.get("funnel_stage", "unknown")] += 1
        source_counts[source] += 1
        for s in segs:
            segment_counts[s] += 1
        cluster_counts[cluster_names.get(cluster_id, str(cluster_id))] += 1

    # ---- convert to serializable dicts ----
    def _top(counter: Counter, k: int = 10) -> list[dict[str, Any]]:
        return [{"label": lbl, "count": c, "pct": round(100 * c / n, 1)} for lbl, c in counter.most_common(k)]

    # ---- co-occurrence matrix (behaviour x barrier) ----
    all_behs = sorted(beh_counts.keys())
    all_bars = sorted(bar_counts.keys())
    co_matrix = []
    for b in all_behs:
        row = {"behaviour": b}
        for br in all_bars:
            row[br] = beh_bar_co[b].get(br, 0)
        co_matrix.append(row)

    return {
        "total": n,
        "behaviours": _top(beh_counts),
        "barriers": _top(bar_counts),
        "unmet_needs": _top(need_counts),
        "intents": _top(intent_counts),
        "funnel_stages": _top(funnel_counts),
        "sources": _top(source_counts),
        "segments": _top(segment_counts),
        "themes": _top(cluster_counts),
        "co_occurrence": co_matrix,
        "source_behaviour": {s: _top(c) for s, c in source_beh.items()},
        "source_barrier": {s: _top(c) for s, c in source_bar.items()},
        "segment_behaviour": {s: _top(c) for s, c in seg_beh.items()},
        "segment_barrier": {s: _top(c) for s, c in seg_bar.items()},
    }
