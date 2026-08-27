"""Optional LLM relevance classifier provider.

Provider resolution (auto): Groq if GROQ_API_KEY is set, else Gemini if
GOOGLE_API_KEY is set, else OpenAI if OPENAI_API_KEY is set, else Anthropic
if ANTHROPIC_API_KEY is set, else None (rules-only offline).

Groq: free, fast, uses llama/mixtral models via OpenAI-compatible API.
Gemini: free tier, uses gemini-2.0-flash via google-generativeai.
Both work without spending money. Prompts and model versions are pinned (EC-42).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

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
        self.provider = None
        self.model = None
        self._choose_provider(c)

    def _choose_provider(self, c: dict[str, Any]) -> None:
        mode = c.get("provider", "auto")
        if mode == "none":
            return

        # Groq (free, fast) — highest priority
        if mode in ("auto", "groq") and os.environ.get("GROQ_API_KEY"):
            self.provider = "groq"
            self.model = c.get("groq_model", "llama-3.1-8b-instant")
            return

        # Gemini (free tier)
        if mode in ("auto", "gemini") and os.environ.get("GOOGLE_API_KEY"):
            self.provider = "gemini"
            self.model = c.get("gemini_model", "gemini-2.0-flash")
            return

        # OpenAI (paid fallback)
        if mode in ("auto", "openai") and os.environ.get("OPENAI_API_KEY"):
            self.provider = "openai"
            self.model = c.get("openai_model", "gpt-4o-mini")
            return

        # Anthropic (paid fallback)
        if mode in ("auto", "anthropic") and os.environ.get("ANTHROPIC_API_KEY"):
            self.provider = "anthropic"
            self.model = c.get("anthropic_model", "claude-3-5-sonnet-latest")
            return

    def available(self) -> bool:
        return self.provider is not None

    def classify(self, text: str) -> dict[str, Any] | None:
        if not self.available():
            return None
        try:
            raw = self._call(text)
            if raw is None:
                return None
            return self._parse(raw)
        except Exception:
            return None

    def _call(self, text: str) -> str | None:
        system = "You are the relevance gate for fashion e-commerce research."
        user_msg = PROMPT + text

        if self.provider == "groq":
            from groq import Groq
            resp = Groq().chat.completions.create(
                model=self.model, temperature=self.temperature, max_tokens=300,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
            )
            return resp.choices[0].message.content

        if self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
            model = genai.GenerativeModel(self.model)
            resp = model.generate_content(
                f"{system}\n\n{user_msg}",
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature, max_output_tokens=300,
                ),
            )
            return resp.text

        if self.provider == "openai":
            from openai import OpenAI
            resp = OpenAI().chat.completions.create(
                model=self.model, temperature=self.temperature, max_tokens=300,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
            )
            return resp.choices[0].message.content

        if self.provider == "anthropic":
            from anthropic import Anthropic
            resp = Anthropic().messages.create(
                model=self.model, max_tokens=300, temperature=self.temperature,
                system=system, messages=[{"role": "user", "content": user_msg}],
            )
            return resp.content[0].text

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
        if not isinstance(obj, dict) or "relevant" not in obj:
            return None
        obj["category"] = obj.get("category", "not_relevant")
        obj["reason"] = str(obj.get("reason", ""))[:300]
        return obj
