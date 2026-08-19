"""Phase 2 tests: raw schema, dedup, storage, fixtures collection, reporting."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src.raw import build_record, normalize_text, record_hash, validate_record, stable_id
from src.storage import Storage
from src.orchestrator import Orchestrator

EXPECTED_KEPT = {
    "reddit_web": 7,
    "app_store": 5,
    "google_play": 5,
    "youtube_comments": 5,
    "quora": 3,
    "forums_blogs": 3,
    "product_reviews": 4,
    "amazon": 3,
    "csv_import": 4,
}
EXPECTED_TOTAL = sum(EXPECTED_KEPT.values())


@pytest.fixture()
def orch(tmp_path: Path):
    return Orchestrator(Storage(tmp_path / "raw", tmp_path / "db" / "corpus.sqlite3"))


# ---- raw.py ------------------------------------------------------------
def test_normalize_text_ignores_case_and_whitespace():
    assert normalize_text("  Buy   the DRESS says 1 ") == normalize_text("buy the dress says 1")
    assert record_hash("  Buy   the DRESS says 1 ") == record_hash("buy the dress says 1")


def test_stable_id_is_deterministic():
    assert stable_id("reddit", "abc") == stable_id("reddit", "abc")
    assert stable_id("reddit", "abc") != stable_id("reddit", "xyz")


def test_validate_record_rejects_bad_records():
    bad = build_record("reddit_web", "x", "", "hello")
    assert any("url" in e for e in validate_record(bad))
    bad2 = build_record("mars", "x", "https://e", "hello")
    assert any("unknown source" in e for e in validate_record(bad2))
    bad3 = build_record("reddit_web", "x", "https://e", "s")
    assert any("too short" in e for e in validate_record(bad3))


# ---- orchestrator / fixtures ------------------------------------------
def test_fixture_collection_end_to_end(orch):
    stats = orch.collect_fixtures()
    assert {s: stats[s]["kept"] for s in EXPECTED_KEPT} == EXPECTED_KEPT
    assert stats["app_store"]["duplicates"] == 1
    assert stats["reddit_web"]["duplicates"] == 1
    assert stats["csv_import"]["invalid"] == 1


def test_all_sources_present_in_corpus(orch, tmp_path):
    orch.collect_fixtures()
    conn = sqlite3.connect(str(tmp_path / "db" / "corpus.sqlite3"))
    conn.row_factory = sqlite3.Row
    present = {r["source"] for r in conn.execute("SELECT DISTINCT source FROM conversations")}
    assert present == set(EXPECTED_KEPT)
    conn.close()


def test_all_kept_records_have_required_fields_and_url(orch, tmp_path):
    orch.collect_fixtures()
    conn = sqlite3.connect(str(tmp_path / "db" / "corpus.sqlite3"))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM conversations").fetchall()
    assert len(rows) == EXPECTED_TOTAL
    for row in rows:
        assert row["id"] and row["source"] and row["source_external_id"]
        assert row["url"].startswith("http")
        assert len(row["text"]) >= 3
    conn.close()


def test_cross_run_dedup_adds_nothing_new(orch, tmp_path):
    orch.collect_fixtures()
    before = orch.storage.count()
    stats2 = orch.collect_fixtures()
    assert orch.storage.count() == before
    assert all(s["kept"] == 0 for s in stats2.values())


def test_within_run_duplicate_is_marked(orch, tmp_path):
    orch.collect_fixtures()
    conn = sqlite3.connect(str(tmp_path / "db" / "corpus.sqlite3"))
    conn.row_factory = sqlite3.Row
    reddit = conn.execute("SELECT * FROM conversations WHERE source='reddit_web'").fetchall()
    texts = {r["text"] for r in reddit}
    assert len(reddit) == EXPECTED_KEPT["reddit_web"]
    assert len(texts) == EXPECTED_KEPT["reddit_web"]
    assert all(r["is_duplicate_of"] is None for r in reddit)
    conn.close()


def test_jsonl_snapshots_only_contain_kept_records(orch, tmp_path):
    orch.collect_fixtures()
    raw_dir = tmp_path / "raw"
    for source, expected in EXPECTED_KEPT.items():
        files = list(raw_dir.glob(f"{source}__*.jsonl"))
        assert files, f"no snapshot for {source}"
        n = sum(len(f.read_text(encoding="utf-8").splitlines()) for f in files)
        assert n == expected, f"{source}: snapshot line count mismatch"


def test_report_lists_sources_and_url_coverage(orch, tmp_path):
    stats = orch.collect_fixtures()
    from src.report import render_report

    report = render_report(tmp_path / "db" / "corpus.sqlite3", stats, "offline fixtures")
    for source in EXPECTED_KEPT:
        assert source in report
    assert "100% of kept conversations carry a source URL." in report
    assert f"**Total kept conversations:** {EXPECTED_TOTAL}" in report


# ---- adapter availability ---------------------------------------------
def test_live_adapters_raise_gracefully_without_credentials(tmp_path):
    from src.adapters import get_adapter
    from src.adapters.base import AdapterContext, SourceUnavailable

    orch = Orchestrator(Storage(tmp_path / "raw", tmp_path / "db" / "corpus.sqlite3"))
    for name in ("reddit", "google_play", "app_store", "youtube_comments", "quora"):
        with pytest.raises(SourceUnavailable):
            list(orch._records(name, AdapterContext(config={})))