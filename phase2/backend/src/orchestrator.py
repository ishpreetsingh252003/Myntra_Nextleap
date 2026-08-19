"""Collection orchestrator: runs adapters, dedups, persists, records runs."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from .adapters import get_adapter
from .adapters.base import AdapterContext, SourceUnavailable
from .raw import stable_id, validate_record, now_iso
from .storage import Storage

# Sources that provide offline fixtures via the web_json / csv adapters.
FIXTURE_SOURCES = {
    "reddit_web": ("web_json", {"schema": "reddit", "fixture_pattern": "reddit_web_sample.json"}),
    "app_store": ("web_json", {"schema": "app_store", "fixture_pattern": "app_store_sample.json"}),
    "google_play": ("web_json", {"schema": "google_play", "fixture_pattern": "google_play_sample.json"}),
    "youtube_comments": ("web_json", {"schema": "youtube", "fixture_pattern": "youtube_comments_sample.json"}),
    "quora": ("web_json", {"schema": "custom", "fixture_pattern": "quora_sample.json"}),
    "forums_blogs": ("web_json", {"schema": "custom", "fixture_pattern": "forums_blogs_sample.json"}),
    "product_reviews": ("web_json", {"schema": "custom", "fixture_pattern": "product_reviews_sample.json"}),
    "amazon": ("web_json", {"schema": "custom", "fixture_pattern": "amazon_sample.json"}),
    "csv_import": ("csv_import", {}),
}


def _run_id() -> str:
    return now_iso().replace(":", "").replace("+", "")[:19].replace("-", "")[:15]


class Orchestrator:
    """Collects via adapters, applying within-run and cross-run dedup."""

    def __init__(self, storage: Storage):
        self.storage = storage
        self.adapter_log: list[str] = []

    def collect_fixtures(self, sources: list[str] | None = None) -> dict[str, dict[str, Any]]:
        sources = sources or list(FIXTURE_SOURCES)
        self.adapter_log.append("MODE: offline fixtures (deterministic sample data)")
        adapter_calls = []
        for src in sources:
            adapter_name, base_config = FIXTURE_SOURCES[src]
            config = dict(base_config)
            config["source_name"] = src
            config["use_fixtures"] = True
            adapter_calls.append((adapter_name, config))
        return self.collect(adapter_calls, run_label="fixtures")

    def collect(self, adapter_calls: list[tuple[str, dict[str, Any]]], run_label: str = "") -> dict[str, dict[str, Any]]:
        run_id = f"{run_label}_{_run_id()}" if run_label else _run_id()
        self.storage.start_run(run_id)
        per_source: dict[str, dict[str, Any]] = {}
        snapshots: dict[str, Path] = {}
        seen_hashes: dict[str, str] = {}

        for adapter_name, adapter_config in adapter_calls:
            source_name = adapter_config.get("source_name", adapter_name)
            ctx = AdapterContext(config=adapter_config)
            stats = {"collected": 0, "kept": 0, "duplicates": 0, "invalid": 0, "errors": []}
            per_source[source_name] = stats
            snapshots[source_name] = self.storage.snapshot_path(source_name)

            try:
                adapters_iter = self._records(adapter_name, ctx)
                for record in adapters_iter:
                    stats["collected"] += 1
                    action = self._process_one(record, source_name, seen_hashes, stats)
                    if action == "kept":
                        self.storage.save_record(record)
                        self.storage.append_jsonl(snapshots[source_name], record)
            except SourceUnavailable as exc:
                stats["errors"].append(exc.message)

            ctx.info(f"{adapter_name}: {stats}")
            self.adapter_log.extend(ctx.log)

        summary = self._summary(per_source)
        self.storage.finish_run(run_id, per_source, summary)
        return per_source

    def _records(self, adapter_name: str, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        """Deliver records from the adapter's fixtures (offline) or live mode."""
        adapter = get_adapter(adapter_name)
        if ctx.config.get("use_fixtures"):
            yield from adapter.from_fixtures(ctx)
        else:
            yield from adapter.run(ctx)

    def _process_one(self, record, source_name, seen_hashes, stats) -> str:
        """Classify a record as kept/duplicate/invalid. Returns the action."""
        errors = validate_record(record)
        if errors:
            stats["invalid"] += 1
            stats["errors"].append("; ".join(errors))
            return "invalid"
        record["source"] = source_name
        record["id"] = stable_id(record["source"], record["source_external_id"])

        # cross-run duplicate by (source, external_id) -> already present
        prior_id = self.storage.already_collected(record["source"], record["source_external_id"])
        if prior_id:
            stats["duplicates"] += 1
            return "duplicate"
        # within-run duplicate by text hash
        hash_key = (record["raw_hash"], record["source"])
        if hash_key in seen_hashes:
            record["is_duplicate_of"] = seen_hashes[hash_key]
            stats["duplicates"] += 1
            return "duplicate"
        seen_hashes[hash_key] = record["id"]
        # cross-source exact duplicate by normalized text hash
        dup = self.storage.find_by_hash(record["raw_hash"], exclude_id=record["id"])
        if dup and dup != record["id"]:
            record["is_duplicate_of"] = dup
            stats["duplicates"] += 1
            return "duplicate"
        stats["kept"] += 1
        return "kept"

    def _summary(self, per_source: dict[str, dict[str, Any]]) -> str:
        total_kept = sum(s["kept"] for s in per_source.values())
        total_dup = sum(s["duplicates"] for s in per_source.values())
        total_invalid = sum(s["invalid"] for s in per_source.values())
        return (
            f"kept={total_kept} duplicates={total_dup} invalid={total_invalid} "
            f"sources={len(per_source)}"
        )