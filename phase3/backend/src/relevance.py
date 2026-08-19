"""Relevance classifier — keyword rules + optional LLM structured output.

Decision rule (EC-18): keyword rules are a pre-filter/scorer; when an LLM provider
is configured the LLM is the decision-maker, otherwise the rule scorer decides.
The final label is always recorded with a decision_source and classifier_version.
"""
from __future__ import annotations

import re
from typing import Any

from .cleaning import normalize_text
from .llm import LLMClassifier


def _terms_re(terms: list[str]) -> list[re.Pattern]:
    return [re.compile(r"\b" + re.escape(t) + r"\b", re.IGNORECASE) for t in terms]


class RelevanceClassifier:
    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg
        self.version = str(cfg.get("classifier_version", "rules-v1.0"))
        rules = cfg.get("rules", {})
        self.min_strong = int(rules.get("min_strong_hits", 1))
        self.min_signal = int(rules.get("min_signal_hits", 2))
        self.strong_w = float(rules.get("strong_weight", 3.0))
        self.signal_w = float(rules.get("signal_weight", 1.0))
        self.categories: dict[str, dict[str, Any]] = {}
        for cat in cfg.get("categories", []):
            self.categories[cat["id"]] = {
                "label": cat.get("label", cat["id"]),
                "strong": _terms_re(cat.get("strong", [])),
                "signal": _terms_re(cat.get("signal", [])),
            }
        self.llm = LLMClassifier(cfg)

    @property
    def llm_available(self) -> bool:
        return self.llm.available()

    def _rule_score(self, text: str) -> tuple[str, int, list[str], list[str]]:
        """Return (best_category, weighted_score, strong_hits, signal_hits)."""
        best_cat, best_score = "not_relevant", 0
        best_strong, best_signal = [], []
        for cat_id, spec in self.categories.items():
            strong_hits = [m.group(0) for rx in spec["strong"] if (m := rx.search(text))][:6]
            signal_hits = [m.group(0) for rx in spec["signal"] if (m := rx.search(text))][:8]
            score = len(strong_hits) * self.strong_w + len(signal_hits) * self.signal_w
            if score > best_score:
                best_cat, best_score = cat_id, int(score)
                best_strong, best_signal = strong_hits, signal_hits
        return best_cat, best_score, best_strong, best_signal

    def classify(self, text: str) -> dict[str, Any]:
        normal = normalize_text(text)
        cat, score, strong, signal = self._rule_score(normal)
        reason_parts = []
        if strong:
            reason_parts.append("strong: " + ", ".join(strong))
        if signal:
            reason_parts.append("signals: " + ", ".join(signal))

        rule_relevant = bool(strong) and len(strong) >= self.min_strong or score >= self.min_signal * self.signal_w
        rule_relevant = rule_relevant and cat != "not_relevant"

        # LLM is the decision-maker when available (EC-18); else rules decide.
        llm_out = self.llm.classify(normal) if self.llm.available() else None
        if llm_out is not None:
            relevant = bool(llm_out.get("relevant"))
            category = llm_out.get("category", "not_relevant")
            reason = llm_out.get("reason", "")
            decision = "llm"
            confidence = "high" if relevant else "medium"
            model_info = f"{self.llm.provider}:{self.llm.model}"
        else:
            relevant = rule_relevant
            category = (cat if rule_relevant else "not_relevant")
            reason = "; ".join(reason_parts) or ("no shopping signals matched" if not rule_relevant else "matched")
            decision = "rules"
            confidence = "high" if strong and relevant else ("medium" if relevant or score >= self.min_signal else "low")
            model_info = "-"

        return {
            "relevant": relevant,
            "relevance_category": category,
            "relevance_reason": reason,
            "relevance_confidence": confidence,
            "decision_source": decision,
            "model": model_info,
            "classifier_version": self.version + (f"+{self.llm.prompt_version}" if decision == "llm" else ""),
        }