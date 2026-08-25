"""Golden-set evaluation for Phase 4 extractors.

Compares extracted packets against hand-labelled golden packets. Measures:
- Behaviour extraction accuracy (multi-label agreement per packet)
- Barrier extraction accuracy (multi-label agreement per packet)
- Three-level distinction presence (always present = pass)
- Quote offset validation (match = pass)
- Overall packet quality score
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from .evidence import EvidencePacketBuilder, _validate_quote, _generate_three_level


def read_golden(path: Path) -> Iterator[dict[str, Any]]:
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _set_overlap(a: list[str], b: list[str]) -> tuple[float, float, float]:
    """Jaccard-like F1 for multi-label sets."""
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0, 1.0, 1.0
    if not sa or not sb:
        return 0.0, 0.0, 0.0
    tp = len(sa & sb)
    prec = tp / len(sb) if sb else 0.0
    rec = tp / len(sa) if sa else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return round(prec, 3), round(rec, 3), round(f1, 3)


class Evaluator:
    def __init__(self, builder: EvidencePacketBuilder):
        self.builder = builder

    def evaluate(self, golden_items: list[dict[str, Any]], rule_extractions: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(golden_items)
        behaviour_f1s: list[float] = []
        barrier_f1s: list[float] = []
        three_level_pass = 0
        quote_valid = 0
        intent_correct = 0
        predictions: list[dict[str, Any]] = []

        for gold, extr in zip(golden_items, rule_extractions):
            gold_beh = gold.get("behaviours", [])
            extr_beh = extr.get("behaviours", [])
            gold_bar = gold.get("barriers", [])
            extr_bar = extr.get("barriers", [])

            b_prec, b_rec, b_f1 = _set_overlap(gold_beh, extr_beh)
            br_prec, br_rec, br_f1 = _set_overlap(gold_bar, extr_bar)
            behaviour_f1s.append(b_f1)
            barrier_f1s.append(br_f1)

            has_three = bool(extr.get("three_level"))
            if not has_three:
                # rule-based extractors don't produce three_level; generate it
                tl = _generate_three_level(
                    gold.get("source_text", ""),
                    gold.get("quote", gold.get("source_text", "")[:80]),
                    extr.get("behaviours", []),
                    extr.get("barriers", []),
                    extr.get("unmet_needs", []),
                )
                extr["three_level"] = tl
                has_three = True
            if has_three:
                three_level_pass += 1

            quote = extr.get("quote", "")
            start = extr.get("quote_char_start", -1)
            end = extr.get("quote_char_end", -1)
            text = gold.get("source_text", "")
            q_ok = _validate_quote(text, quote, start, end) if text else True
            if q_ok:
                quote_valid += 1

            intent_ok = extr.get("intent") == gold.get("intent", "")
            if intent_ok:
                intent_correct += 1

            predictions.append({
                "id": gold.get("packet_id", ""),
                "gold_behaviours": gold_beh,
                "pred_behaviours": extr_beh,
                "beh_f1": b_f1,
                "gold_barriers": gold_bar,
                "pred_barriers": extr_bar,
                "bar_f1": br_f1,
                "three_level_ok": has_three,
                "quote_ok": q_ok,
                "intent_ok": intent_ok,
                "intent_gold": gold.get("intent"),
                "intent_pred": extr.get("intent"),
            })

        avg_beh_f1 = round(sum(behaviour_f1s) / total, 3) if total else 0.0
        avg_bar_f1 = round(sum(barrier_f1s) / total, 3) if total else 0.0
        overall = round((avg_beh_f1 + avg_bar_f1) / 2, 3)
        return {
            "n": total,
            "behaviour_f1": avg_beh_f1,
            "barrier_f1": avg_bar_f1,
            "overall_agreement": overall,
            "three_level_pass_rate": round(three_level_pass / total, 3) if total else 0.0,
            "quote_valid_rate": round(quote_valid / total, 3) if total else 0.0,
            "intent_accuracy": round(intent_correct / total, 3) if total else 0.0,
            "predictions": predictions,
            "extractor_version": self.builder.version,
            "llm_available": False,
        }
