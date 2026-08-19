"""Optional LLM relevance classifier provider.

Provider resolution (auto): Anthropic if ANTHROPIC_API_KEY is set, else OpenAI if
OPENAI_API_KEY is set, else None. With no provider the rule classifier is the
decision-maker and runs fully offline (EC-39/EC-41: graceful, never a stack
trace). Prompts and model versions are pinned so runs are reproducible (EC-42).
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


PROMPT = """You decide whether an online shopping conversation is relevant to our
research: why users add fashion items to a wishlist but never buy within 30 days.
Relevant means the author talks about their own (or closely observed) shopping:
wishlist/save-for-later, purchase intention or hesitation, product comparison,
fit/size/quality doubts, occasion or gift shopping, review-checking, or shopping
app/delivery/returns experience. NOT relevant: pure promo/spam/bot text, songs
called a playlist/wishlist, already-purchased completion stories with no decision
content, unrelated products.

Return ONLY JSON:
{"relevant": true|false, "category": "<one of wishlist_bookmark, purchase_intent,
purchase_hesitation, product_comparison, fit_size_quality, occasion_gift_shopping,
shopping_experience, review_checking, not_relevant>", "reason": "<short reason>"}

Conversation:
"""


class LLMClassifier:
    def __init__(self, cfg: dict[str, Any]) -> None:
        c = cfg.get("llm", {})
        self.temperature = float(c.get("temperature", 0.0))
        self.versioned = bool(c.get("versioned", True))
        self.prompt_version = "relevance-v1"
        self._choose_provider(c)

    def _choose_provider(self, c: dict[str, Any]) -> None:
        self.provider = None
        self.model = None
        self.client = None
        mode = c.get("provider", "auto")
        if mode == "none":
            return
        key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not key:
            return
        if mode == "auto" or mode == "anthropic":
            if os.environ.get("ANTHROPIC_API_KEY"):
                try:
                    import anthropic  # noqa: F401

                    self.provider = "anthropic"
                    self.model = c.get("anthropic_model", "claude-3-5-sonnet-latest")
                    self.client = "anthropic"
                    return
                except ImportError:
                    pass
            if os.environ.get("OPENAI_API_KEY"):
                try:
                    import openai  # noqa: F401

                    self.provider = "openai"
                    self.model = c.get("openai_model", "gpt-4o-mini")
                    self.client = "openai"
                except ImportError:
                    self.provider = "anthropic"
            return
        if mode == "openai" and os.environ.get("OPENAI_API_KEY"):
            try:
                import openai  # noqa: F401

                self.provider = "openai"
                self.model = c.get("openai_model", "gpt-4o-mini")
                self.client = "openai"
            except ImportError:
                pass

    def available(self) -> bool:
        return self.provider is not None and self.client is not None

    def classify(self, text: str) -> dict[str, Any] | None:
        """Return parsed JSON {relevant, category, reason} or None if unavailable/failed."""
        if not self.available():
            return None
        import anthropic
        import openai

        try:
            if self.provider == "anthropic":
                message = anthropic.Anthropic().messages.create(
                    model=self.model,
                    max_tokens=300,
                    temperature=self.temperature,
                    system="You are the relevance gate for fashion e-commerce research.",
                    messages=[{"role": "user", "content": PROMPT + text}],
                )
                raw = message.content[0].text
            else:
                completion = openai.OpenAI().chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=300,
                    messages=[
                        {"role": "system", "content": "You are the relevance gate for fashion e-commerce research."},
                        {"role": "user", "content": PROMPT + text},
                    ],
                )
                raw = completion.choices[0].message.content or ""
        except Exception:
            return None
        return self._parse(raw)

    def _parse(self, raw: str) -> dict[str, Any] | None:
        fence = _JSON_FENCE.search(raw)
        if fence:
            raw = fence.group(1)
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            # tolerate a leading/trailing { } without wrapping list
            start, end = raw.find("{"), raw.rfind("}")
            if start == -1:
                return None
            try:
                obj = json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                return None
        if not isinstance(obj, dict) or "relevant" not in obj:
            return None
        obj["category"] = obj.get("category", "not_relevant")
        obj["reason"] = str(obj.get("reason", ""))[:300]
        return obj