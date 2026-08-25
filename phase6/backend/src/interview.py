"""Interview Question Generator — 2-3 open-ended questions per ranked opportunity.

Questions are designed for the 5-6 primary interviews the PM will conduct
after using the Discovery Engine.
"""
from __future__ import annotations

from typing import Any


def generate_questions(opportunity: dict[str, Any], n: int = 3) -> list[str]:
    """Generate open-ended interview questions for an opportunity."""
    title = opportunity.get("title", "this area")
    behaviours = opportunity.get("behaviours", [])
    barriers = opportunity.get("barriers", [])

    questions: list[str] = []

    # universal opener
    questions.append(
        f"Can you walk me through a time when you were shopping for fashion online "
        f"and {title.replace('_', ' ')} affected your decision?"
    )

    # behaviour-specific
    if any(b in behaviours for b in ["shortlist_products", "bookmark_for_later"]):
        questions.append(
            f"When you save items to your wishlist, what usually happens next? "
            f"Do you come back to them, or do they get forgotten?"
        )
    if any(b in behaviours for b in ["compare_products", "check_fit", "check_quality"]):
        questions.append(
            f"What information do you wish you had when comparing products or checking fit/quality?"
        )
    if any(b in behaviours for b in ["wait_before_buying", "price_track"]):
        questions.append(
            f"What would make you buy immediately instead of waiting for a sale?"
        )

    # barrier-specific
    if any(b in barriers for b in ["fit_uncertainty", "size_uncertainty"]):
        questions.append(
            f"How do you currently decide which size to pick? What would make you more confident?"
        )
    if any(b in barriers for b in ["quality_uncertainty", "reality_uncertainty"]):
        questions.append(
            f"How much do product photos influence your purchase decision? "
            f"What would help you trust what you see?"
        )

    # close with solution space
    questions.append(
        f"If you could change one thing about the shopping experience for '{title.replace('_', ' ')}', "
        f"what would it be?"
    )

    return questions[:n]
