"""Phase 5 tests: segmentation, clustering, quantification, pipeline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.clustering import cluster_packets
from src.config import load_config
from src.evaluator import validate
from src.pipeline import Pipeline
from src.quantification import quantify
from src.segmentation import assign_segments
from src.storage import Storage
from src.cli import read_jsonl

P5 = Path(__file__).resolve().parents[2]
PACKETS = Path(r"D:\myntra_nextleap\phase4\data\output\evidence_packets.jsonl")


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture()
def sample_packets():
    return [
        {"packet_id": "EP-0001", "quote": "I keep adding kurtas to my Myntra wishlist", "behaviours": ["shortlist_products"], "barriers": ["forgetting"], "unmet_needs": [], "intent": "save_for_later", "funnel_stage": "saved", "user_role": "self", "segment_hints": [], "source": "reddit", "source_url": "http://e"},
        {"packet_id": "EP-0002", "quote": "Been waiting for this dress to go on sale", "behaviours": ["wait_before_buying", "price_track"], "barriers": ["price_uncertainty"], "unmet_needs": ["price_transparency"], "intent": "save_for_later", "funnel_stage": "hesitating", "user_role": "self", "segment_hints": ["SEG-07"], "source": "reddit", "source_url": "http://e"},
        {"packet_id": "EP-0003", "quote": "Comparing kurtas on Myntra and AJIO, can't decide", "behaviours": ["compare_products", "check_fit"], "barriers": ["comparison_bloat", "fit_uncertainty"], "unmet_needs": ["fit_guidance"], "intent": "purchase", "funnel_stage": "evaluating", "user_role": "self", "segment_hints": ["SEG-09"], "source": "app_store", "source_url": "http://e"},
        {"packet_id": "EP-0004", "quote": "Sizing is unreliable, saved it but stuck", "behaviours": ["check_fit", "shortlist_products"], "barriers": ["size_uncertainty"], "unmet_needs": ["fit_guidance"], "intent": "save_for_later", "funnel_stage": "hesitating", "user_role": "self", "segment_hints": ["SEG-10"], "source": "google_play", "source_url": "http://e"},
        {"packet_id": "EP-0005", "quote": "Saving sarees for my sister's wedding, checking reviews", "behaviours": ["shop_for_occasion", "check_reviews", "shortlist_products"], "barriers": ["reality_uncertainty"], "unmet_needs": ["quality_trust"], "intent": "occasion", "funnel_stage": "evaluating", "user_role": "self", "segment_hints": ["SEG-04"], "source": "youtube", "source_url": "http://e"},
        {"packet_id": "EP-0006", "quote": "Looking for a birthday gift for my mom", "behaviours": ["gift_shopping", "compare_products", "shortlist_products"], "barriers": ["comparison_bloat"], "unmet_needs": ["comparison_tool"], "intent": "gift", "funnel_stage": "evaluating", "user_role": "self", "segment_hints": ["SEG-06"], "source": "reddit", "source_url": "http://e"},
        {"packet_id": "EP-0007", "quote": "Delivery was late, exchange took forever", "behaviours": ["check_reviews"], "barriers": ["delivery_concern", "return_concern"], "unmet_needs": ["quality_trust"], "intent": "unknown", "funnel_stage": "abandoned", "user_role": "self", "segment_hints": [], "source": "app_store", "source_url": "http://e"},
        {"packet_id": "EP-0008", "quote": "M vs L for this kurta, which to pick", "behaviours": ["compare_products", "check_fit", "check_reviews"], "barriers": ["fit_uncertainty", "comparison_bloat"], "unmet_needs": ["fit_guidance"], "intent": "purchase", "funnel_stage": "evaluating", "user_role": "self", "segment_hints": ["SEG-09", "SEG-10"], "source": "app_store", "source_url": "http://e"},
    ]


# ---- segmentation --------------------------------------------------------
def test_segment_assignment_multi_label(sample_packets):
    pkt = sample_packets[0]
    segs = assign_segments(pkt, [])
    assert "SEG-03" in segs  # shortlist_products -> high_wishlist_user
    assert "SEG-05" in segs  # user_role self


def test_segment_occasion(sample_packets):
    pkt = sample_packets[4]
    segs = assign_segments(pkt, [])
    assert "SEG-04" in segs  # shop_for_occasion
    assert "SEG-06" not in segs  # not a gift


def test_segment_gift(sample_packets):
    pkt = sample_packets[5]
    segs = assign_segments(pkt, [])
    assert "SEG-06" in segs  # gift intent


def test_segment_budget(sample_packets):
    pkt = sample_packets[1]
    segs = assign_segments(pkt, [])
    assert "SEG-07" in segs  # price_track


# ---- clustering -----------------------------------------------------------
def test_clustering_produces_labels(sample_packets, cfg):
    result = cluster_packets(sample_packets, cfg)
    assert len(result["labels"]) == len(sample_packets)
    assert result["n_clusters"] >= 2
    assert result["cluster_labels"]
    assert isinstance(result["silhouette"], float)


# ---- quantification -------------------------------------------------------
def test_quantification_covers_all_dimensions(sample_packets, cfg):
    cluster_result = cluster_packets(sample_packets, cfg)
    quant = quantify(sample_packets, cluster_result["labels"], cluster_result["cluster_labels"])
    assert quant["total"] == 8
    assert len(quant["behaviours"]) > 0
    assert len(quant["barriers"]) > 0
    assert len(quant["segments"]) > 0
    assert len(quant["sources"]) > 0
    assert len(quant["co_occurrence"]) > 0


def test_quantification_percentages(sample_packets, cfg):
    cluster_result = cluster_packets(sample_packets, cfg)
    quant = quantify(sample_packets, cluster_result["labels"], cluster_result["cluster_labels"])
    total_pct = sum(item["pct"] for item in quant["behaviours"])
    assert total_pct > 100  # multi-label, so > 100%


# ---- pipeline end-to-end --------------------------------------------------
def test_pipeline_end_to_end(tmp_path, cfg):
    if not PACKETS.exists():
        pytest.skip("phase4 evidence packets not available")
    storage = Storage(tmp_path / "out")
    pipeline = Pipeline(storage, cfg)
    stats = pipeline.run(read_jsonl(PACKETS))
    assert stats["total_packets"] > 0
    assert stats["clusters"] >= 2
    assert storage.count_packets() == stats["total_packets"]


# ---- evaluator ------------------------------------------------------------
def test_validate_passes_for_good_quantification():
    quant = {
        "segments": [{"label": "SEG-03", "count": 5}, {"label": "SEG-07", "count": 4}],
        "themes": [{"label": "theme A", "count": 6}, {"label": "theme B", "count": 4}],
    }
    result = validate(quant)
    assert result["pass"]


def test_validate_fails_for_small_clusters():
    quant = {
        "segments": [{"label": "SEG-01", "count": 1}],
        "themes": [{"label": "tiny", "count": 2}],
    }
    result = validate(quant)
    assert not result["pass"]
    assert len(result["issues"]) >= 2
