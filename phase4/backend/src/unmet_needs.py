"""Rule-based unmet-need inference — what information, trust, or experience was missing.

Unmet needs are kept distinct from raw quotes (architecture §6.3). They are
inferred from the conversation's barrier signals + explicit "missing" language.
"""
from __future__ import annotations

import re
from typing import Any


def _kw_match(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if re.search(re.escape(kw), text, re.IGNORECASE)]


class UnmetNeedInferrer:
    def __init__(self, cfg: dict[str, Any]):
        self.need_signals: dict[str, list[str]] = {}
        for name, keywords in cfg.get("unmet_needs", {}).items():
            self.need_signals[name] = keywords if isinstance(keywords, list) else []

    def infer(self, text: str, barriers: list[str]) -> list[str]:
        normal = text.lower()
        needs: list[str] = []
        for need, keywords in self.need_signals.items():
            if _kw_match(normal, keywords):
                needs.append(need)
        if not needs:
            for barrier in barriers:
                mapped = {
                    "fit_uncertainty": "fit_guidance",
                    "size_uncertainty": "fit_guidance",
                    "quality_uncertainty": "quality_trust",
                    "reality_uncertainty": "quality_trust",
                    "price_uncertainty": "price_transparency",
                    "spend_hesitation": "price_transparency",
                    "review_doubt": "review_reliability",
                    "social_validation_missing": "social_proof",
                    "styling_uncertainty": "styling_help",
                    "comparison_bloat": "comparison_tool",
                    "availability_issue": "quality_trust",
                }
                if barrier in mapped and mapped[barrier] not in needs:
                    needs.append(mapped[barrier])
        return needs
