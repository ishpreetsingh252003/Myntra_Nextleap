"""Golden-set evaluation for the relevance classifier.

Computes agreement and per-class precision/recall/F1 between classifier output
and the hand-labelled golden set. Works fully offline with rule-based decisions;
when an LLM is configured it reports the LLM-sourced metrics instead.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterator

from .relevance import RelevanceClassifier


def read_golden(path: Path) -> Iterator[dict[str, Any]]:
    """Accept .jsonl (one dict per line) or .csv (id,text,gold_label[,gold_category])."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with open(path, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                yield {
                    "id": row.get("id", ""),
                    "text": row.get("text", ""),
                    "gold_label": row.get("gold_label", ""),
                    "gold_category": row.get("gold_category", ""),
                }
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            yield item


class Evaluator:
    def __init__(self, classifier: RelevanceClassifier):
        self.classifier = classifier

    def evaluate(self, golden_items: list[dict[str, Any]]) -> dict[str, Any]:
        conf = {"relevant": {"TP": 0, "FP": 0, "FN": 0},
                "not_relevant": {"TP": 0, "FP": 0, "FN": 0}}
        correct = 0
        category_ok = category_n = 0
        predictions: list[dict[str, Any]] = []

        for item in golden_items:
            pred = self.classifier.classify(item.get("text", ""))
            gold = item.get("gold_label", "not_relevant").lower().strip()
            gold_cat = (item.get("gold_category") or "").lower().strip()
            pred_cls = "relevant" if pred["relevant"] else "not_relevant"
            gold_cls = "relevant" if gold in ("1", "true", "yes", "relevant") else "not_relevant"
            for cls in ("relevant", "not_relevant"):
                t = conf[cls]
                if pred_cls == cls and gold_cls == cls:
                    t["TP"] += 1
                elif pred_cls == cls and gold_cls != cls:
                    t["FP"] += 1
                elif gold_cls == cls and pred_cls != cls:
                    t["FN"] += 1
            if pred_cls == gold_cls:
                correct += 1
            is_relevant = pred["relevant"]
            if gold_cls == "relevant" and gold_cat:
                category_n += 1
                if pred["relevance_category"] == gold_cat:
                    category_ok += 1
            predictions.append({
                "id": item.get("id", ""),
                "gold_label": gold,
                "gold_category": gold_cat,
                "pred_relevant": is_relevant,
                "pred_category": pred["relevance_category"],
                "confidence": pred["relevance_confidence"],
                "decision_source": pred["decision_source"],
                "reason": pred["relevance_reason"],
                "correct": pred_cls == gold_cls,
                "text": item.get("text", "")[:120],
            })

        n = len(golden_items)
        metrics = {}
        for cls in ("relevant", "not_relevant"):
            tp, fp, fn = conf[cls]["TP"], conf[cls]["FP"], conf[cls]["FN"]
            prec = tp / (tp + fp) if (tp + fp) else 0.0
            rec = tp / (tp + fn) if (tp + fn) else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
            metrics[cls] = {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3), "n": tp + fn}
        return {
            "n": n,
            "agreement": round(correct / n, 3) if n else 0.0,
            "correct": correct,
            "metrics": metrics,
            "category_accuracy": round(category_ok / category_n, 3) if category_n else None,
            "category_evaluated": category_n,
            "predictions": predictions,
            "classifier_version": self.classifier.version,
            "llm_available": self.classifier.llm_available,
        }