"""Optional LLM extraction provider — Claude/GPT structured output.

Provider resolution: Anthropic if ANTHROPIC_API_KEY set, else OpenAI if OPENAI_API_KEY
set, else None. With no provider the rule-based extractors run fully offline (EC-39/41).
Prompts and model versions are pinned per run (EC-42).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class LLMUnavailable(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


EXTRACTION_PROMPT = """You are an expert fashion e-commerce researcher extracting structured evidence
from online conversations about fashion shopping (wishlist, buying, sizing, quality, etc.).

Given the conversation text below, extract:
1. behaviours: list of behaviour labels (from: shortlist_products, compare_products, wait_before_buying, check_fit, check_quality, seek_social_validation, shop_for_occasion, bookmark_for_later, price_track, gift_shopping, self_shopping, check_reviews)
2. barriers: list of barrier labels (from: fit_uncertainty, size_uncertainty, quality_uncertainty, reality_uncertainty, styling_uncertainty, occasion_uncertainty, review_doubt, authenticity_concern, price_uncertainty, spend_hesitation, comparison_bloat, social_validation_missing, availability_issue, delivery_concern, return_concern, low_urgency, forgetting, pure_bookmarking, none_stated)
3. unmet_needs: list of what was missing (information, trust, functionality, experience)
4. user_role: self / other / unknown
5. funnel_stage: saved / evaluating / hesitating / abandoned / purchased / unknown
6. intent: purchase / bookmark / save_for_later / occasion / gift / unknown
7. segment_hints: list of segment IDs if clear (SEG-01..SEG-10, or empty)
8. three_level: { said: <verbatim quote>, inferred: <what behaviour/inference>, concluded: <opportunity hypothesis> }
9. confidence: { behaviours: high/medium/low, barriers: high/medium/low, intent: high/medium/low }
10. quote_char_start: character offset of the chosen quote in the original text
11. quote_char_end: end offset

Return ONLY a JSON object matching this schema. Use multi-label: extract ALL that apply.
When no barrier is stated, use barriers: ["none_stated"]. Never invent barriers.

Conversation text:
"""


class LLMExtractor:
    def __init__(self, cfg: dict[str, Any]) -> None:
        c = cfg.get("llm", {})
        self.temperature = float(c.get("temperature", 0.0))
        self.versioned = bool(c.get("versioned", True))
        self.prompt_version = "extraction-v1"
        self._choose_provider(c)

    def _choose_provider(self, c: dict[str, Any]) -> None:
        self.provider = None
        self.model = None
        self.client = None
        mode = c.get("provider", "auto")
        if mode == "none":
            return
        if mode in ("auto", "anthropic") and os.environ.get("ANTHROPIC_API_KEY"):
            try:
                import anthropic  # noqa: F401
                self.provider = "anthropic"
                self.model = c.get("anthropic_model", "claude-3-5-sonnet-latest")
                self.client = "anthropic"
                return
            except ImportError:
                pass
        if mode in ("auto", "openai") and os.environ.get("OPENAI_API_KEY"):
            try:
                import openai  # noqa: F401
                self.provider = "openai"
                self.model = c.get("openai_model", "gpt-4o-mini")
                self.client = "openai"
                return
            except ImportError:
                pass

    def available(self) -> bool:
        return self.provider is not None and self.client is not None

    def extract(self, text: str) -> dict[str, Any] | None:
        if not self.available():
            return None
        raw = self._call(text)
        if raw is None:
            return None
        return self._parse(raw)

    def _call(self, text: str) -> str | None:
        try:
            if self.provider == "anthropic":
                import anthropic
                message = anthropic.Anthropic().messages.create(
                    model=self.model, max_tokens=800,
                    temperature=self.temperature,
                    system="You extract structured evidence from fashion e-commerce conversations.",
                    messages=[{"role": "user", "content": EXTRACTION_PROMPT + text}],
                )
                return message.content[0].text
            else:
                import openai
                completion = openai.OpenAI().chat.completions.create(
                    model=self.model, temperature=self.temperature, max_tokens=800,
                    messages=[
                        {"role": "system", "content": "You extract structured evidence from fashion e-commerce conversations."},
                        {"role": "user", "content": EXTRACTION_PROMPT + text},
                    ],
                )
                return completion.choices[0].message.content
        except Exception:
            return None

    def _parse(self, raw: str) -> dict[str, Any] | None:
        fence = _JSON_FENCE.search(raw)
        if fence:
            raw = fence.group(1)
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1:
            return None
        try:
            obj = json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return None
        if not isinstance(obj, dict):
            return None
        obj["behaviours"] = [b for b in obj.get("behaviours", []) if isinstance(b, str)]
        obj["barriers"] = [b for b in obj.get("barriers", []) if isinstance(b, str)]
        obj["unmet_needs"] = [n for n in obj.get("unmet_needs", []) if isinstance(n, str)]
        obj["segment_hints"] = [s for s in obj.get("segment_hints", []) if isinstance(s, str)]
        return obj
