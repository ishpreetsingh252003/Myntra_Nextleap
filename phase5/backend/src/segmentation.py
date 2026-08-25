"""Segment assignment — derives user segments from evidence packets.

Uses the Phase 1 candidate segmentation taxonomy (SEG-01..SEG-10).
Each packet gets assigned one or more segments based on its behaviours,
barriers, and text signals. Multi-segment membership is allowed (EC-28).
"""
from __future__ import annotations

import re
from typing import Any


def assign_segments(packet: dict[str, Any], segment_rules: list[dict[str, Any]]) -> list[str]:
    """Assign segment IDs to a packet based on behaviours + text signals."""
    assigned: list[str] = []
    text = (packet.get("quote", "") or "").lower()
    behaviours = packet.get("behaviours", [])
    barriers = packet.get("barriers", [])
    intent = packet.get("intent", "")
    user_role = packet.get("user_role", "")

    # SEG-01 first_time_shopper: explicit signal
    # SEG-02 frequent_shopper: explicit signal
    # SEG-03 high_wishlist_user: shortlist_products behaviour
    if "shortlist_products" in behaviours:
        assigned.append("SEG-03")

    # SEG-04 occasion_shopper: shop_for_occasion behaviour
    if "shop_for_occasion" in behaviours or intent == "occasion":
        assigned.append("SEG-04")

    # SEG-05 shopping_for_self: user_role self
    if user_role == "self":
        assigned.append("SEG-05")

    # SEG-06 shopping_for_others: user_role other OR gift intent
    if user_role == "other" or intent == "gift":
        assigned.append("SEG-06")

    # SEG-07 budget_conscious: price_track behaviour OR price barriers
    if "price_track" in behaviours or any(b in barriers for b in ["price_uncertainty", "spend_hesitation"]):
        assigned.append("SEG-07")

    # SEG-08 fashion_conscious: check_quality or check_fit behaviours
    if "check_quality" in behaviours or "check_fit" in behaviours:
        assigned.append("SEG-08")

    # SEG-09 multi_product_comparer: compare_products behaviour
    if "compare_products" in behaviours:
        assigned.append("SEG-09")

    # SEG-10 repeated_sizing_concern: fit/size barriers
    if any(b in barriers for b in ["fit_uncertainty", "size_uncertainty"]):
        assigned.append("SEG-10")

    # Also check rule-based signals from config
    for seg in segment_rules:
        seg_id = seg["id"]
        if seg_id in assigned:
            continue
        hits = [s for s in seg.get("signals", []) if s.lower() in text]
        if hits and seg_id not in assigned:
            assigned.append(seg_id)

    return list(dict.fromkeys(assigned))  # deduplicate, preserve order
