"""Opportunity Scorer — weighted scoring formula (architecture §5.1).

Each opportunity is scored across 8 dimensions with transparent breakdown.
The score determines ranking; the breakdown explains why.
"""
from __future__ import annotations

from typing import Any


DEFAULT_WEIGHTS = {
    "frequency": 0.20,
    "severity": 0.15,
    "purchase_impact": 0.20,
    "users_affected": 0.10,
    "evidence_strength": 0.15,
    "segment_concentration": 0.05,
    "existing_workaround": 0.10,
    "product_leverage": 0.05,
}


def score_opportunity(
    theme_label: str,
    behaviours: list[str],
    barriers: list[str],
    frequency: int,
    total_packets: int,
    segment_concentration: float,
    evidence_strength: str,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Score a single opportunity area. Returns score + breakdown."""
    w = weights or DEFAULT_WEIGHTS

    # ---- dimension scores (0-1 scale) ----
    freq_score = min(frequency / max(total_packets, 1), 1.0)

    high_severity_barriers = {"fit_uncertainty", "size_uncertainty", "quality_uncertainty",
                               "reality_uncertainty", "delivery_concern", "return_concern"}
    sev_hits = len(set(barriers) & high_severity_barriers)
    sev_score = min(sev_hits / 3, 1.0)

    purchase_blockers = {"fit_uncertainty", "size_uncertainty", "quality_uncertainty",
                          "reality_uncertainty", "comparison_bloat", "price_uncertainty"}
    pi_hits = len(set(barriers) & purchase_blockers)
    pi_score = min(pi_hits / 3, 1.0)

    users_score = segment_concentration

    strength_map = {"high": 1.0, "medium": 0.6, "low": 0.3}
    ev_score = strength_map.get(evidence_strength, 0.5)

    seg_score = min(segment_concentration * 2, 1.0)

    workaround_indicators = {"comparison_bloat", "price_uncertainty", "review_doubt"}
    aw_hits = len(set(barriers) & workaround_indicators)
    aw_score = min(aw_hits / 2, 1.0)

    leverage_indicators = {"check_fit", "check_quality", "check_reviews", "compare_products"}
    pl_hits = len(set(behaviours) & leverage_indicators)
    pl_score = min(pl_hits / 2, 1.0)

    breakdown = {
        "frequency": round(freq_score * w["frequency"], 4),
        "severity": round(sev_score * w["severity"], 4),
        "purchase_impact": round(pi_score * w["purchase_impact"], 4),
        "users_affected": round(users_score * w["users_affected"], 4),
        "evidence_strength": round(ev_score * w["evidence_strength"], 4),
        "segment_concentration": round(seg_score * w["segment_concentration"], 4),
        "existing_workaround": round(aw_score * w["existing_workaround"], 4),
        "product_leverage": round(pl_score * w["product_leverage"], 4),
    }
    total_score = round(sum(breakdown.values()), 4)

    return {
        "title": theme_label,
        "score": total_score,
        "breakdown": breakdown,
        "frequency": frequency,
        "behaviours": behaviours,
        "barriers": barriers,
        "evidence_strength": evidence_strength,
    }


def rank_opportunities(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort opportunities by score descending and assign ranks."""
    ranked = sorted(opportunities, key=lambda o: o["score"], reverse=True)
    for i, opp in enumerate(ranked):
        opp["rank"] = i + 1
    return ranked
