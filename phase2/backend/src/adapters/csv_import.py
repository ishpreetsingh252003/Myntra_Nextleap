"""Manual CSV import adapter (fallback when a source is unavailable)."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterator

from ..raw import build_record
from .base import AdapterContext, SourceUnavailable

REQUIRED_COLUMNS = {"source", "external_id", "url", "text"}


class CsvImportAdapter:
    """Reads a CSV of conversations (header row above).

    Columns: source, external_id, url, text[, author, timestamp, likes, comments]
    """

    name = "csv_import"

    def from_fixtures(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        file = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "csv_import_sample.csv"
        if not file.exists():
            raise SourceUnavailable(f"csv fixture missing: {file}")
        yield from self._read(str(file))

    def run(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        files = ctx.config.get("files", [])
        if not files:
            raise SourceUnavailable("csv_import needs 'files' containing CSV paths")
        for file in files:
            yield from self._read(file)

    def _read(self, path: str) -> Iterator[dict[str, Any]]:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            columns = reader.fieldnames or []
            missing = REQUIRED_COLUMNS - set(columns)
            if missing:
                raise SourceUnavailable(f"csv missing columns: {sorted(missing)}")
            for row in reader:
                if not row.get("text") and not row.get("url"):
                    continue
                yield build_record(
                    source=row["source"],
                    source_external_id=row["external_id"],
                    url=row["url"],
                    text=row["text"],
                    author=row.get("author"),
                    timestamp=row.get("timestamp"),
                    engagement={
                        k: int(v) if v and v.lstrip("-").isdigit() else v
                        for k, v in (("likes", row.get("likes")), ("comments", row.get("comments")))
                        if v
                    },
                )