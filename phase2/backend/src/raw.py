"""Raw conversation record: schema, hashing, validation (architecture plan 6.1)."""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

REQUIRED_FIELDS = ("source", "source_external_id", "url", "text")
VALID_SOURCES = {
    "google_play",
    "app_store",
    "reddit",
    "reddit_web",
    "youtube_comments",
    "quora",
    "forums_blogs",
    "product_reviews",
    "amazon",
    "csv_import",
}


def now_iso() -> str:
    """UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def normalize_text(text: str) -> str:
    """Normalize casing + whitespace for stable hashing."""
    return re.sub(r"\s+", " ", str(text).strip().casefold())


def record_hash(text: str) -> str:
    """Deterministic hash of normalized text used for exact/near dedup key."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def stable_id(source: str, external_id: str) -> str:
    """Deterministic primary key for a conversation record."""
    return hashlib.sha1(f"{source}:{external_id}".encode("utf-8")).hexdigest()[:16]


def build_record(
    source: str,
    source_external_id: str,
    url: str,
    text: str,
    *,
    author: str | None = None,
    timestamp: str | None = None,
    engagement: dict[str, Any] | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """Build a raw conversation record. All list-level fields assigned here."""
    if source_external_id is None or source_external_id == "":
        source_external_id = str(uuid.uuid4())
    if url is None:
        url = ""
    return {
        "id": None,  # assigned by storage after dedup
        "source": source,
        "source_external_id": str(source_external_id),
        "url": url,
        "author": author,
        "timestamp": timestamp,
        "text": text,
        "language": language,
        "engagement_metrics": engagement or {},
        "collected_at": now_iso(),
        "raw_hash": record_hash(text),
        "is_duplicate_of": None,
    }


def validate_record(record: dict[str, Any]) -> list[str]:
    """Return list of problems with a record. Empty list == record is valid."""
    errors = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            errors.append(f"missing required field: {field}")
    if record.get("source") not in VALID_SOURCES:
        errors.append(f"unknown source: {record.get('source')!r}")
    if record.get("text") and len(record["text"].strip()) < 3:
        errors.append("text too short to be meaningful (<3 chars)")
    return errors