"""Rule-based barrier extractor — multi-label from keyword signals.

Maps to the Phase 1 hypothesis library (PB-01..PB-18). When no barrier
keyword matches, returns ["none_stated"] per EC-20. Never invents a barrier.
"""
from __future__ import annotations

import re
from typing import Any


def _kw_match(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE)]


class RuleBarrierExtractor:
    def __init__(self, cfg: dict[str, Any]):
        self.taxonomy: dict[str, dict[str, Any]] = {}
        for b in cfg.get("barriers", []):
            self.taxonomy[b["name"]] = {"id": b["id"], "keywords": b.get("keywords", [])}

    def extract(self, text: str) -> dict[str, Any]:
        normal = text.lower()
        barriers: list[str] = []
        conf: dict[str, str] = {}
        for name, spec in self.taxonomy.items():
            hits = _kw_match(normal, spec["keywords"])
            if hits:
                barriers.append(name)
                conf[name] = "high" if len(hits) >= 2 else "medium"
        if not barriers:
            barriers = ["none_stated"]
            conf["none_stated"] = "high"
        return {"barriers": barriers, "barrier_confidence": conf}
