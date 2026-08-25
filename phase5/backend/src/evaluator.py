"""Golden-set evaluation for Phase 5 segmentation + clustering.

Validates that every segment and theme is traceable to >= 3 evidence packets
(architecture exit criteria).
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def validate(quantification: dict[str, Any], min_size: int = 3) -> dict[str, Any]:
    """Validate quantification against architecture exit criteria."""
    issues: list[str] = []
    segments = quantification.get("segments", [])
    themes = quantification.get("themes", [])

    for seg in segments:
        if seg["count"] < min_size:
            issues.append(f"segment '{seg['label']}' has only {seg['count']} packets (need >= {min_size})")

    for theme in themes:
        if theme["count"] < min_size:
            issues.append(f"theme '{theme['label']}' has only {theme['count']} packets (need >= {min_size})")

    if not segments:
        issues.append("no segments found")
    if not themes:
        issues.append("no themes found")

    return {
        "pass": len(issues) == 0,
        "issues": issues,
        "n_segments": len(segments),
        "n_themes": len(themes),
        "min_segment_size": min(s["count"] for s in segments) if segments else 0,
        "min_theme_size": min(t["count"] for t in themes) if themes else 0,
    }
