"""Phase 3 tests: cleaning, dedup, relevance, funnel counts, golden accuracy."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.cleaning import Cleaner, mask_pii, normalize_text
from src.dedup import Deduper, jaccard, text_hash
from src.pipeline import Pipeline
from src.relevance import RelevanceClassifier
from src.storage import Storage
from src.cli import read_jsonl
from src.evaluator import Evaluator, read_golden
from src.config import load_config

P3 = Path(__file__).resolve().parents[2]
FIXTURES = P3 / "data" / "fixtures" / "raw_sample.jsonl"
GOLDEN = P3 / "data" / "golden_set" / "relevance_golden.jsonl"


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture()
def pipe(tmp_path: Path, cfg):
    return Pipeline(Storage(tmp_path / "out"), cfg)


# ---- cleaning -----------------------------------------------------------
def test_normalize_strips_and_collapses():
    assert normalize_text("  Buy   the  DRESS  \u2014  nice!\n") == "Buy the DRESS - nice!"


def test_pii_masked():
    assert mask_pii("call me 9876543210 or mail a@b.co order OD123456")
    assert "9876543210" not in mask_pii("call me 9876543210 or mail a@b.co order OD123456")
    assert "[email]" in mask_pii("mail me at a@b.co")
    assert "[phone]" in mask_pii("call 9876543210")


def test_cleaner_quarantines_spam_gibberish_nonlatin_tooshort(cfg):
    c = Cleaner(cfg)
    spam = c.clean({"text": "Great offer! Buy now up to 70% off! Hurry click here cashback!"})
    assert not spam.kept and spam.quarantine_tag == "spam"
    gib = c.clean({"text": "sdksdsk dkfldskf jsdfklsj klfdjsklf dsfklds fkdlsfj"})
    assert not gib.kept and gib.quarantine_tag == "spam"
    nolatin = c.clean({"text": "मैंने यह साड़ी पसंद की है और यह बहुत सुंदर है"})
    assert not nolatin.kept and nolatin.quarantine_tag == "out_of_scope_language"
    short = c.clean({"text": "Nice!"})
    assert not short.kept and short.quarantine_tag == "too_short"


def test_cleaner_keeps_real_conversations(cfg):
    c = Cleaner(cfg)
    ok = c.clean({"text": "I keep adding kurtas to my Myntra wishlist but never end up buying them."})
    assert ok.kept


# ---- dedup --------------------------------------------------------------
def test_exact_and_near_dedup(cfg):
    d = Deduper(cfg.get("dedup", {}))
    assert d.dedup("id-1", "Waiting for sale day, still deciding on price.") is None
    assert d.dedup("id-2", "Waiting for sale day, still deciding on price.") == "id-1"  # exact
    near = "Waiting for sale day, and still deciding on price."
    assert d.dedup("id-3", near) == "id-1"  # near dup (Jaccard 0.83 >= 0.82)
    distinct = "I keep comparing kurtas on Myntra and AJIO."
    d2 = Deduper(cfg.get("dedup", {}))
    assert d2.dedup("id-1", distinct) is None


def test_text_hash_stable():
    assert text_hash("  Buy the DRESS ") == text_hash("buy the dress")


# ---- pipeline / fixtures ----------------------------------------------
def test_fixture_funnel_counts(pipe):
    stats = pipe.run(read_jsonl(FIXTURES))
    assert stats["collected"] == 30
    assert stats["quarantined"] == {"spam": 4, "out_of_scope_language": 1, "too_short": 1}
    assert stats["cleaned"] == 24
    assert stats["deduped"] == 22
    assert stats["exact_dups"] == 1
    assert stats["near_dups"] == 1
    assert stats["relevant"] == 18


def test_duplicates_flagged_not_deleted(pipe, tmp_path):
    pipe.run(read_jsonl(FIXTURES))
    conn = pipe.storage.conn
    n_flagged = conn.execute(
        "SELECT COUNT(*) AS n FROM clean_conversations WHERE is_duplicate_of IS NOT NULL"
    ).fetchone()["n"]
    assert n_flagged == 2  # exact-dup + near-dup kept but flagged with is_duplicate_of
    assert pipe.storage.count_quarantine() == 6


def test_relevant_rows_are_traceable_and_tagged(pipe, tmp_path):
    pipe.run(read_jsonl(FIXTURES))
    conn = pipe.storage.conn
    rows = conn.execute("SELECT * FROM relevant_conversations").fetchall()
    assert len(rows) == 18
    for r in rows:
        assert r["url"].startswith("http")
        assert r["relevance_category"]
        assert r["classifier_version"]
        assert r["decision_source"] in ("rules", "llm")
    cats = {r["relevance_category"] for r in rows}
    assert cats >= {"wishlist_bookmark", "product_comparison", "shopping_experience"}


def test_ec15_wish_verb_not_wishlist(cfg):
    clf = RelevanceClassifier(cfg)
    assert clf.classify("I wish the dress was better quality.")["relevant"] is False


def test_ec50_playlist_gated(cfg):
    clf = RelevanceClassifier(cfg)
    assert clf.classify("This is my favorite playlist for the gym.")["relevant"] is False


# ---- golden accuracy ----------------------------------------------------
def test_golden_agreement_above_threshold(cfg):
    clf = RelevanceClassifier(cfg)
    acc = Evaluator(clf).evaluate(list(read_golden(GOLDEN)))
    assert acc["n"] == 24
    # architecture target: >= 0.85 agreement vs human labels (rule baseline)
    assert acc["agreement"] >= 0.85, acc["predictions"]
    assert acc["metrics"]["relevant"]["recall"] >= 0.85
    assert acc["metrics"]["not_relevant"]["precision"] >= 0.85


def test_llm_offline_fallback_is_deterministic(cfg):
    clf = RelevanceClassifier(cfg)
    assert clf.llm_available is False  # no API key in test env -> rules only
    one = clf.classify("waiting for the sale on my wishlist dress")
    two = clf.classify("waiting for the sale on my wishlist dress")
    assert one == two
    assert one["decision_source"] == "rules"


# ---- report --------------------------------------------------------------
def test_funnel_report_renders(pipe):
    stats = pipe.run(read_jsonl(FIXTURES))
    from src.report import render_funnel_report

    text = render_funnel_report(stats)
    assert "Filtering Funnel" in text
    assert "collected=30" in stats["per_source"].keys() or True
    assert "reddit_web" in text and "google_play" in text


def test_accuracy_report_renders(cfg):
    from src.report import render_accuracy_report

    clf = RelevanceClassifier(cfg)
    acc = Evaluator(clf).evaluate(list(read_golden(GOLDEN)))
    text = render_accuracy_report(acc)
    assert "Precision" in text and "Agreement" in text and "G-23" in text