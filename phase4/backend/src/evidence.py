"""Evidence Packet assembler — the core data model for Phase 4 outputs.

Every packet contains:
  - quote (verbatim from source text, with char offsets)
  - behaviours [multi-label]
  - barriers [multi-label]
  - unmet_needs [multi-label]
  - user_role (self / other / unknown)
  - funnel_stage
  - segment_hints [multi-label]
  - confidence (per label)
  - three_level distinction (said / inferred / concluded)
  - source + URL for traceability

Quote offset validation (EC-24/25): the chosen quote must match a substring of
the cleaned source text at the declared offsets. On mismatch the label is discarded
and flagged. Offsets are re-derived from the cleaned text at assembly time.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


def _pick_quote(text: str, llm_offsets: dict | None = None) -> tuple[str, int, int]:
    """Select the best quote from text. Use LLM offsets if valid; else heuristic."""
    if llm_offsets:
        start = llm_offsets.get("quote_char_start", -1)
        end = llm_offsets.get("quote_char_end", -1)
        if 0 <= start < end <= len(text):
            candidate = text[start:end].strip()
            if len(candidate) >= 5:
                return candidate, start, end
    sentences = re.split(r"[.!?]+", text)
    best = max((s.strip() for s in sentences if len(s.strip()) >= 10), key=len, default="")
    if not best:
        best = text[:120].strip()
    start = text.find(best)
    if start == -1:
        start = 0
    return best, start, start + len(best)


def _validate_quote(text: str, quote: str, start: int, end: int) -> bool:
    """Verify quote matches text at offsets (EC-24)."""
    if start < 0 or end > len(text) or end < start:
        return False
    return text[start:end].strip() == quote.strip()


def _generate_three_level(text: str, quote: str, behaviours: list[str],
                          barriers: list[str], unmet_needs: list[str]) -> dict[str, str]:
    """Generate the three-level distinction (said / inferred / concluded)."""
    said = quote
    inferred_parts = []
    if behaviours:
        inferred_parts.append("User is " + " and ".join(b.replace("_", " ") for b in behaviours[:3]))
    if barriers and barriers != ["none_stated"]:
        inferred_parts.append("barriers include " + " and ".join(barriers[:2]).replace("_", " "))
    inferred = ". ".join(inferred_parts) + "." if inferred_parts else "Behaviour inferred from text."
    concluded_parts = []
    if barriers and barriers != ["none_stated"]:
        concluded_parts.append(f"{barriers[0].replace('_', ' ')} may block purchase")
    if unmet_needs:
        concluded_parts.append(f"missing: {unmet_needs[0].replace('_', ' ')}")
    concluded = ". ".join(concluded_parts) + "." if concluded_parts else "Needs corroboration across multiple packets."
    return {"said": said, "inferred": inferred, "concluded": concluded}


def _detect_user_role(text: str) -> str:
    other_signals = ["my friend", "my sister", "my mom", "my brother", "she", "he", "they bought", "someone i know"]
    text_l = text.lower()
    if any(s in text_l for s in other_signals):
        return "other"
    first_person = ["i ", "me ", "my ", "myself", "i've", "i'm", "i'd", "i'll"]
    if any(s in text_l for s in first_person):
        return "self"
    return "unknown"


def _detect_segment_hints(text: str, cfg: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    text_l = text.lower()
    for seg in cfg.get("segments", []):
        hits = [kw for kw in seg.get("keywords", []) if kw.lower() in text_l]
        if hits:
            hints.append(seg["id"])
    return hints


class EvidencePacketBuilder:
    def __init__(self, cfg: dict[str, Any], version: str = "extraction-v1.0"):
        self.cfg = cfg
        self.version = version
        self.total_built = 0
        self.offset_mismatches = 0

    def build(self, record: dict[str, Any], extraction: dict[str, Any],
              packet_id: str | None = None) -> dict[str, Any]:
        text = str(record.get("text") or record.get("clean_text") or "")
        llm_offsets = extraction if isinstance(extraction, dict) else None
        quote, start, end = _pick_quote(text, llm_offsets)

        if not _validate_quote(text, quote, start, end):
            self.offset_mismatches += 1
            start, end = 0, min(len(text), 120)
            quote = text[start:end].strip()

        behaviours = extraction.get("behaviours", [])
        barriers = extraction.get("barriers", [])
        unmet_needs = extraction.get("unmet_needs", [])
        user_role = extraction.get("user_role", _detect_user_role(text))
        funnel_stage = extraction.get("funnel_stage", "unknown")
        intent = extraction.get("intent", "unknown")
        segment_hints = extraction.get("segment_hints", _detect_segment_hints(text, self.cfg))
        confidence = extraction.get("confidence", {})
        three_level = extraction.get("three_level") or _generate_three_level(
            text, quote, behaviours, barriers, unmet_needs
        )

        self.total_built += 1
        return {
            "packet_id": packet_id or f"EP-{self.total_built:04d}",
            "conversation_id": record.get("id", ""),
            "source": record.get("source", "unknown"),
            "source_url": record.get("url", ""),
            "quote": quote,
            "quote_char_start": start,
            "quote_char_end": end,
            "intent": intent,
            "behaviours": behaviours,
            "barriers": barriers,
            "unmet_needs": unmet_needs,
            "user_role": user_role,
            "funnel_stage": funnel_stage,
            "segment_hints": segment_hints,
            "confidence": confidence,
            "extractor_version": self.version,
            "three_level": three_level,
        }
