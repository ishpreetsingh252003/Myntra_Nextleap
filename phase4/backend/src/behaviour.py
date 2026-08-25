"""Rule-based behaviour extractor — multi-label from keyword signals.

Matches against the Phase 1 behaviour taxonomy. Each matched behaviour gets
a confidence (high if ≥2 keywords, medium if 1). Works fully offline (EC-39).
"""
from __future__ import annotations

import re
from typing import Any


def _kw_match(text: str, keywords: list[str]) -> list[str]:
    """Return which keywords matched in text."""
    return [kw for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE)]


def _kw_match_any(text: str, keywords: list[str]) -> bool:
    return bool(_kw_match(text, keywords))


class RuleBehaviourExtractor:
    def __init__(self, cfg: dict[str, Any]):
        self.taxonomy: dict[str, dict[str, Any]] = {}
        for b in cfg.get("behaviours", []):
            self.taxonomy[b["name"]] = {"id": b["id"], "keywords": b.get("keywords", [])}
        self.funnel: dict[str, list[str]] = {}
        for stage, sig in cfg.get("funnel", {}).items():
            self.funnel[stage] = sig.get("keywords", [])

    def extract(self, text: str) -> dict[str, Any]:
        normal = text.lower()
        behaviours: list[str] = []
        conf: dict[str, str] = {}
        for name, spec in self.taxonomy.items():
            hits = _kw_match(normal, spec["keywords"])
            if hits:
                behaviours.append(name)
                conf[name] = "high" if len(hits) >= 2 else "medium"
        funnel_stage = self._detect_funnel(normal)
        intent = self._detect_intent(normal, behaviours)
        return {
            "behaviours": behaviours,
            "behaviour_confidence": conf,
            "funnel_stage": funnel_stage,
            "intent": intent,
        }

    def _detect_funnel(self, text: str) -> str:
        scores: dict[str, int] = {}
        for stage, kws in self.funnel.items():
            scores[stage] = len(_kw_match(text, kws))
        best = max(scores, key=scores.get)  # type: ignore
        return best if scores[best] > 0 else "unknown"

    def _detect_intent(self, text: str, behaviours: list[str]) -> str:
        if "gift_shopping" in behaviours:
            return "gift"
        if "shop_for_occasion" in behaviours:
            return "occasion"
        if "bookmark_for_later" in behaviours and "shortlist_products" not in behaviours:
            return "bookmark"
        if "shortlist_products" in behaviours or "price_track" in behaviours:
            return "save_for_later"
        if "compare_products" in behaviours or "check_fit" in behaviours or "check_quality" in behaviours:
            return "purchase"
        return "unknown"
