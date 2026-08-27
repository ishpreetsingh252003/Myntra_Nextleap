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

    def extract(self, text: str) -> dict[str, Any] | None:
        if not self.available():
            return None
        raw = self._call(text)
        if raw is None:
            return None
        return self._parse(raw)

    def _call(self, text: str) -> str | None:
        system = "You extract structured evidence from fashion e-commerce conversations."
        user_msg = EXTRACTION_PROMPT + text
        try:
            if self.provider == "groq":
                from groq import Groq
                resp = Groq().chat.completions.create(
                    model=self.model, temperature=self.temperature, max_tokens=800,
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
                        temperature=self.temperature, max_output_tokens=800,
                    ),
                )
                return resp.text
            if self.provider == "openai":
                from openai import OpenAI
                completion = OpenAI().chat.completions.create(
                    model=self.model, temperature=self.temperature, max_tokens=800,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
                )
                return completion.choices[0].message.content
            if self.provider == "anthropic":
                from anthropic import Anthropic
                message = Anthropic().messages.create(
                    model=self.model, max_tokens=800, temperature=self.temperature,
                    system=system, messages=[{"role": "user", "content": user_msg}],
                )
                return message.content[0].text
        except Exception:
            return None
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
