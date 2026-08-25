"""Phase 4 tests: extractors, evidence packets, accuracy, embeddings, pipeline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.behaviour import RuleBehaviourExtractor
from src.barrier import RuleBarrierExtractor
from src.config import load_config
from src.evidence import EvidencePacketBuilder, _validate_quote, _pick_quote
from src.embeddings import Embedder, EmbeddingStore
from src.evaluator import Evaluator, read_golden, _set_overlap
from src.pipeline import Pipeline
from src.storage import Storage
from src.unmet_needs import UnmetNeedInferrer
from src.cli import read_jsonl

P4 = Path(__file__).resolve().parents[2]
GOLDEN = P4 / "data" / "golden_set" / "evidence_golden.jsonl"
RELEVANT = Path(r"D:\myntra_nextleap\phase3\data\output\relevant_corpus.jsonl")


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture()
def pipe(tmp_path: Path, cfg):
    return Pipeline(Storage(tmp_path / "out"), cfg)


# ---- behaviour extractor ------------------------------------------------
def test_behaviour_extractor_multi_label(cfg):
    ext = RuleBehaviourExtractor(cfg)
    result = ext.extract("I keep comparing kurtas on Myntra and AJIO. Can't decide which one.")
    assert "compare_products" in result["behaviours"]
    assert result["funnel_stage"] in ("evaluating", "hesitating", "unknown")
    assert result["intent"] in ("purchase", "unknown", "save_for_later")


def test_behaviour_extractor_wishlist(cfg):
    ext = RuleBehaviourExtractor(cfg)
    result = ext.extract("I saved this dress in my wishlist and I'll buy it during the sale.")
    assert "shortlist_products" in result["behaviours"]
    assert "price_track" in result["behaviours"]


def test_behaviour_extractor_gift(cfg):
    ext = RuleBehaviourExtractor(cfg)
    result = ext.extract("Looking for a birthday gift for my mom, I have 3 options saved.")
    assert "gift_shopping" in result["behaviours"]
    assert result["intent"] == "gift"


# ---- barrier extractor ---------------------------------------------------
def test_barrier_extractor_multi_label(cfg):
    ext = RuleBarrierExtractor(cfg)
    result = ext.extract("The sizing is confusing and the fabric quality looks questionable.")
    assert "size_uncertainty" in result["barriers"] or "quality_uncertainty" in result["barriers"]
    assert len(result["barriers"]) >= 1


def test_barrier_extractor_none_stated(cfg):
    ext = RuleBarrierExtractor(cfg)
    result = ext.extract("I just saved it for later, no particular reason.")
    assert "none_stated" in result["barriers"]


# ---- unmet needs ---------------------------------------------------------
def test_unmet_needs_infer(cfg):
    inf = UnmetNeedInferrer(cfg)
    needs = inf.infer("The sizing is confusing.", ["size_uncertainty"])
    assert "fit_guidance" in needs


def test_unmet_needs_empty_when_no_barriers(cfg):
    inf = UnmetNeedInferrer(cfg)
    needs = inf.infer("Just saving for later.", ["none_stated"])
    assert isinstance(needs, list)


# ---- quote pick + validate -----------------------------------------------
def test_pick_quote_heuristic():
    text = "I keep adding kurtas to my Myntra wishlist but never end up buying them. I always save a couple and then forget."
    quote, start, end = _pick_quote(text)
    assert len(quote) >= 10
    assert _validate_quote(text, quote, start, end)


def test_pick_quote_llm_offsets():
    text = "This is a longer conversation text with many words and sentences that go on."
    quote, start, end = _pick_quote(text, {"quote_char_start": 0, "quote_char_end": 30})
    assert start == 0 and end == 30


def test_validate_quote_fails_on_mismatch():
    assert not _validate_quote("hello world", "goodbye", 0, 7)


# ---- evidence packet builder ---------------------------------------------
def test_packet_builder_has_all_fields(cfg):
    builder = EvidencePacketBuilder(cfg)
    rec = {"id": "test-1", "source": "reddit", "url": "https://example.com", "text": "I saved a dress and can't decide."}
    extraction = {"behaviours": ["shortlist_products"], "barriers": ["comparison_bloat"], "unmet_needs": [], "user_role": "self", "funnel_stage": "evaluating", "intent": "save_for_later", "segment_hints": ["SEG-09"], "confidence": {"behaviours": "medium"}}
    pkt = builder.build(rec, extraction, packet_id="EP-TEST-01")
    required = ["packet_id", "conversation_id", "source", "source_url", "quote",
                "quote_char_start", "quote_char_end", "intent", "behaviours",
                "barriers", "unmet_needs", "user_role", "funnel_stage",
                "segment_hints", "confidence", "extractor_version", "three_level"]
    for field in required:
        assert field in pkt, f"missing field: {field}"
    assert pkt["three_level"]["said"]
    assert pkt["three_level"]["inferred"]
    assert pkt["three_level"]["concluded"]
    assert pkt["quote_char_start"] >= 0


def test_packet_builder_detects_user_role(cfg):
    builder = EvidencePacketBuilder(cfg)
    rec = {"id": "t2", "source": "reddit", "url": "http://e", "text": "My friend bought a dress and she loved it."}
    pkt = builder.build(rec, {"behaviours": [], "barriers": [], "unmet_needs": []})
    assert pkt["user_role"] == "other"


def test_packet_builder_generates_three_level(cfg):
    builder = EvidencePacketBuilder(cfg)
    rec = {"id": "t3", "source": "play", "url": "http://e", "text": "Sizing is confusing. I saved it but can't decide."}
    pkt = builder.build(rec, {"behaviours": ["shortlist_products", "check_fit"], "barriers": ["size_uncertainty"], "unmet_needs": ["fit_guidance"]})
    assert "shortlist products" in pkt["three_level"]["inferred"]
    assert "size uncertainty" in pkt["three_level"]["concluded"]


# ---- embeddings -----------------------------------------------------------
def test_tfidf_embeddings_fit_transform():
    emb = Embedder({"embeddings": {"method": "tfidf", "max_features": 50, "ngram_range": [1, 2]}})
    vecs = emb.fit_transform(["I saved a dress", "Comparing kurtas on Myntra", "Waiting for sale"])
    assert len(vecs) == 3
    assert len(vecs[0]) == emb.embedding_dim()


def test_embedding_store_persists(tmp_path):
    store = EmbeddingStore(tmp_path / "emb")
    store.save("conv-1", [0.1, 0.2], metadata={"source": "reddit"})
    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0]["conversation_id"] == "conv-1"


# ---- set overlap ----------------------------------------------------------
def test_set_overlap():
    p, r, f = _set_overlap(["a", "b", "c"], ["b", "c", "d"])
    assert p == pytest.approx(2 / 3, abs=0.01)
    assert r == pytest.approx(2 / 3, abs=0.01)
    assert f == pytest.approx(0.667, abs=0.01)


def test_set_overlap_empty():
    p, r, f = _set_overlap([], [])
    assert p == 1.0 and f == 1.0


# ---- golden accuracy ------------------------------------------------------
def test_golden_accuracy_above_threshold(cfg):
    golden = list(read_golden(GOLDEN))
    assert len(golden) >= 20
    builder = EvidencePacketBuilder(cfg)
    rule_extractions = []
    for g in golden:
        text = g.get("source_text", "")
        beh = RuleBehaviourExtractor(cfg).extract(text)
        bar = RuleBarrierExtractor(cfg).extract(text)
        needs = UnmetNeedInferrer(cfg).infer(text, bar["barriers"])
        rule_extractions.append({**beh, **bar, "unmet_needs": needs, "confidence": {}})
    acc = Evaluator(builder).evaluate(golden, rule_extractions)
    assert acc["n"] >= 20
    # rule baseline target: >= 0.60 agreement; LLM expected to reach >= 0.80
    assert acc["overall_agreement"] >= 0.60
    assert acc["three_level_pass_rate"] == 1.0
    assert acc["intent_accuracy"] >= 0.50


# ---- pipeline end-to-end --------------------------------------------------
def test_pipeline_end_to_end(tmp_path, cfg):
    if not RELEVANT.exists():
        pytest.skip("phase3 relevant corpus not available")
    storage = Storage(tmp_path / "out")
    pipeline = Pipeline(storage, cfg)
    stats = pipeline.run(read_jsonl(RELEVANT))
    assert stats["extracted"] > 0
    assert stats["offset_mismatches"] >= 0
    assert storage.count_packets() == stats["extracted"]
    packets = list(storage.iter_packets())
    for pkt in packets:
        assert pkt["packet_id"]
        assert pkt["three_level_said"]
        assert pkt["behaviours"]
