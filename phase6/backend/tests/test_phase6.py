"""Phase 6 tests: scorer, interview questions, evidence DB, pipeline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config import load_config
from src.evidence_db import EvidenceDB
from src.interview import generate_questions
from src.pipeline import Pipeline
from src.scorer import rank_opportunities, score_opportunity
from src.storage import Storage
from src.cli import read_jsonl

P6 = Path(__file__).resolve().parents[2]
PACKETS = Path(r"D:\myntra_nextleap\phase4\data\output\evidence_packets.jsonl")
QUANT = Path(r"D:\myntra_nextleap\phase5\data\output\quantification.json")


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture()
def sample_packets():
    return [
        {"packet_id": "EP-0001", "conversation_id": "c1", "source": "reddit", "source_url": "http://e",
         "quote": "I keep adding kurtas to my wishlist but never buy", "behaviours": ["shortlist_products"],
         "barriers": ["forgetting"], "unmet_needs": [], "intent": "save_for_later",
         "funnel_stage": "saved", "user_role": "self", "segment_hints": ["SEG-03"],
         "cluster_label": "wishlist / forget / save", "cluster_id": 0},
        {"packet_id": "EP-0002", "conversation_id": "c2", "source": "reddit", "source_url": "http://e",
         "quote": "Waiting for sale to buy the dress", "behaviours": ["wait_before_buying", "price_track"],
         "barriers": ["price_uncertainty"], "unmet_needs": ["price_transparency"], "intent": "save_for_later",
         "funnel_stage": "hesitating", "user_role": "self", "segment_hints": ["SEG-07"],
         "cluster_label": "sale / price / wait", "cluster_id": 1},
        {"packet_id": "EP-0003", "conversation_id": "c3", "source": "app_store", "source_url": "http://e",
         "quote": "Sizing is unreliable, M fits but this is tight", "behaviours": ["check_fit", "shortlist_products"],
         "barriers": ["size_uncertainty", "fit_uncertainty"], "unmet_needs": ["fit_guidance"],
         "intent": "save_for_later", "funnel_stage": "hesitating", "user_role": "self",
         "segment_hints": ["SEG-10"], "cluster_label": "fit / size / tight", "cluster_id": 2},
        {"packet_id": "EP-0004", "conversation_id": "c4", "source": "google_play", "source_url": "http://e",
         "quote": "Delivery was late, exchange took forever", "behaviours": ["check_reviews"],
         "barriers": ["delivery_concern", "return_concern"], "unmet_needs": ["quality_trust"],
         "intent": "unknown", "funnel_stage": "abandoned", "user_role": "self", "segment_hints": [],
         "cluster_label": "delivery / return / late", "cluster_id": 3},
    ]


# ---- scorer ---------------------------------------------------------------
def test_score_opportunity_range(cfg):
    opp = score_opportunity("test", ["shortlist_products"], ["forgetting"], 5, 18, 0.3, "high")
    assert 0.0 <= opp["score"] <= 1.0
    assert opp["frequency"] == 5
    assert opp["score"] > 0


def test_rank_opportunities():
    opps = [
        {"title": "low", "score": 0.2, "rank": 0},
        {"title": "high", "score": 0.8, "rank": 0},
        {"title": "mid", "score": 0.5, "rank": 0},
    ]
    ranked = rank_opportunities(opps)
    assert ranked[0]["title"] == "high"
    assert ranked[0]["rank"] == 1
    assert ranked[2]["title"] == "low"


# ---- interview questions ---------------------------------------------------
def test_generate_questions_returns_list():
    opp = {"title": "fit_uncertainty", "behaviours": ["check_fit"], "barriers": ["fit_uncertainty"]}
    qs = generate_questions(opp)
    assert isinstance(qs, list)
    assert len(qs) >= 2
    assert any("size" in q.lower() or "fit" in q.lower() for q in qs)


# ---- evidence DB -----------------------------------------------------------
def test_evidence_db_saves_and_retrieves(tmp_path):
    db = EvidenceDB(tmp_path / "test.db")
    opp = {"rank": 1, "title": "test", "score": 0.5, "behaviours": [], "barriers": [], "evidence_strength": "medium"}
    pkt = {"packet_id": "EP-1", "conversation_id": "c1", "source": "reddit", "source_url": "http://e", "quote": "test quote"}
    db.save_opportunity(opp, [pkt], ["Question 1?"])
    assert db.count_opportunities() == 1
    assert db.count_evidence_links() == 1
    opps = db.get_opportunities()
    assert opps[0]["title"] == "test"
    evidence = db.get_evidence_for_opportunity("OPP-001")
    assert len(evidence) == 1
    db.close()


# ---- pipeline end-to-end ---------------------------------------------------
def test_pipeline_end_to_end(tmp_path, cfg):
    if not PACKETS.exists() or not QUANT.exists():
        pytest.skip("phase4/5 outputs not available")
    storage = Storage(tmp_path / "out")
    evidence_db = EvidenceDB(tmp_path / "out" / "evidence.db")
    pipeline = Pipeline(storage, evidence_db, cfg)
    quant = json.loads(QUANT.read_text(encoding="utf-8"))
    stats = pipeline.run(read_jsonl(PACKETS), quant)
    assert stats["opportunities"] > 0
    assert stats["total_packets"] > 0
    evidence_db.close()
