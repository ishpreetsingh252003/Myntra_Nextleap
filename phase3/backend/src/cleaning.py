"""Phase 3 cleaning transforms.

Pipeline:  raw -> normalize -> mask PII -> validate lengths/script
-> quarantine (spam / promo / bot / out-of-scope language / too-short).

Quarantine never deletes silently: every dropped record is written to the
quarantine corpus with a reason (EC-06, EC-13, EC-14, EC-04, EC-07).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

_WS = re.compile(r"\s+")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_PHONE = re.compile(r"\b(?:\+?\d[\d\s-]{8,14}\d)\b")
_ORDER = re.compile(r"\b(?:OD|OR|M)=\d{4,}\b|\b\d{12}\b")
_HASHTAG = re.compile(r"#\w+")
_URL = re.compile(r"https?://\S+|\bwww\.\S+")
_NON_LATIN = re.compile(r"[^\u0000-\u024F\u1E00-\u1EFF]")


def normalize_text(text: str) -> str:
    """Canonical text for hashing + display. Collapse whitespace, unify quotes/case."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = _WS.sub(" ", text).strip()
    return text


def mask_pii(text: str) -> str:
    """Mask obvious PII before any downstream storage (EC-14). Returns masked text."""
    text = _EMAIL.sub("[email]", text)
    text = _PHONE.sub("[phone]", text)
    text = _ORDER.sub("[order-id]", text)
    return text


@dataclass
class CleanedRecord:
    """One raw record after cleaning + a quarantine decision."""

    raw: dict[str, Any]
    clean_text: str
    masked_text: str
    quarantine_tag: str | None = None   # None = kept
    quarantine_reason: str | None = None
    flags: list[str] = field(default_factory=list)  # informational notes (ngram dup, etc.)

    @property
    def kept(self) -> bool:
        return self.quarantine_tag is None


class Cleaner:
    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg.get("cleaning", {})
        self.spam_cfg = cfg.get("spam", {})
        self.min_chars = int(self.cfg.get("min_text_chars", 10))
        self.edge_latin = float(self.cfg.get("out_of_scope_latin_ratio", 0.35))
        self.link_max = int(self.cfg.get("link_density_max", 6))
        self.promo_terms = [t.casefold() for t in self.spam_cfg.get("promo_terms", [])]
        self.pseudo_alpha = float(self.spam_cfg.get("pseudo_latin", {}).get("max_alpha_signal", 0.35))
        self.repeat_ratio = float(self.spam_cfg.get("repeat", {}).get("max_repeat_ratio", 0.4))

    # ---- quarantine checks ----
    def _quarantine_spam(self, text: str) -> str | None:
        lowered = text.casefold()
        hits = [t for t in self.promo_terms if t in lowered]
        if len(hits) >= 2:
            return f"promo ({', '.join(hits[:3])})"
        url_count = len(_URL.findall(text))
        if url_count > self.link_max:
            return f"link-heavy ({url_count} urls)"
        letters = re.findall(r"[A-Za-z]", lowered)
        if letters and len(letters) >= 8:
            # gibberish bot strings contain long consonant clusters with no vowels
            runs = re.findall(r"[aeiouy]*[^aeiouy\s][^aeiouy\s]*", lowered)
            longest = max((len(r) for r in runs), default=0)
            if any(len(r) >= 5 for r in re.findall(r"[^aeiouy\s]{3,}", lowered)):
                return "bot-like gibberish"
        words = re.findall(r"\b\w+\b", lowered)
        if len(words) >= 4:
            reps = {w: words.count(w) for w in set(words) if len(w) > 2}
            if reps and max(reps.values()) / len(words) >= self.repeat_ratio:
                return "repetitive bot text"
        return None

    def _quarantine_language_out_of_scope(self, text: str) -> str | None:
        """Heavy non-Latin script (mostly Devanagari/Arabic/CJK) -> out of scope (EC-04)."""
        latin = len(_NON_LATIN.sub("", text))
        total = max(len(text), 1)
        if latin / total < 1 - self.edge_latin:
            return "out-of-scope language (non-Latin script)"
        return None

    # ---- main transform ----
    def clean(self, raw: dict[str, Any]) -> CleanedRecord:
        raw_text = str(raw.get("text") or "")
        normal = normalize_text(raw_text)
        masked = mask_pii(normal) if self.cfg.get("pii_mask", True) else normal

        reason = None
        if len(normal) < self.min_chars:
            reason = "too short to be meaningful (<%d chars)" % self.min_chars
        elif self._quarantine_language_out_of_scope(masked) is not None:
            reason = "out-of-scope language (non-Latin script)"
        else:
            sp = self._quarantine_spam(masked)
            if sp:
                reason = "spam: " + sp

        return CleanedRecord(
            raw=raw,
            clean_text=normal,
            masked_text=masked,
            quarantine_tag="spam" if (reason and reason.startswith("spam")) else (
                "out_of_scope_language" if reason and "language" in reason else (
                    "too_short" if reason else None
                )
            ),
            quarantine_reason=reason,
        )