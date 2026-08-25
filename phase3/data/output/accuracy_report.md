# Phase 3 Relevance Classifier Accuracy

- **Generated:** 2026-08-26T02:14:41
- **Golden set size:** 24
- **Agreement (exact label match):** 0.958 (23/24)
- **Classifier version:** rules-v1.0
- **Decision source:** rules (offline baseline)

Target from architecture §4 Phase 3: ≥ 85% agreement vs human labels (LLM as decision-maker). The numbers below are the deterministic rule baseline — LLM typically improves on it when enabled.

| Class | Precision | Recall | F1 | n |
|-------|-----------|--------|----|---|
| relevant | 0.941 | 1.0 | 0.97 | 16 |
| not_relevant | 1.0 | 0.875 | 0.933 | 8 |

Category accuracy (of 16 relevant golden items with a category): 0.75

## Predictions vs gold

| id | gold | gold_cat | pred | pred_cat | conf | ok |
|----|------|----------|------|----------|------|----|
| G-01 | relevant | wishlist_bookmark | relevant | wishlist_bookmark | high | YES |
| G-02 | relevant | purchase_hesitation | relevant | purchase_hesitation | medium | YES |
| G-03 | relevant | product_comparison | relevant | product_comparison | medium | YES |
| G-04 | relevant | fit_size_quality | relevant | wishlist_bookmark | high | YES |
| G-05 | relevant | occasion_gift_shopping | relevant | review_checking | high | YES |
| G-06 | relevant | review_checking | relevant | review_checking | high | YES |
| G-07 | relevant | purchase_intent | relevant | purchase_intent | medium | YES |
| G-08 | relevant | purchase_hesitation | relevant | purchase_hesitation | medium | YES |
| G-09 | relevant | occasion_gift_shopping | relevant | occasion_gift_shopping | medium | YES |
| G-10 | relevant | shopping_experience | relevant | shopping_experience | medium | YES |
| G-11 | relevant | wishlist_bookmark | relevant | wishlist_bookmark | high | YES |
| G-12 | relevant | shopping_experience | relevant | shopping_experience | medium | YES |
| G-13 | relevant | product_comparison | relevant | review_checking | high | YES |
| G-14 | relevant | purchase_hesitation | relevant | wishlist_bookmark | high | YES |
| G-15 | relevant | wishlist_bookmark | relevant | wishlist_bookmark | high | YES |
| G-16 | not_relevant | - | not_relevant | not_relevant | low | YES |
| G-17 | not_relevant | - | not_relevant | not_relevant | low | YES |
| G-18 | not_relevant | - | not_relevant | not_relevant | low | YES |
| G-19 | not_relevant | - | not_relevant | not_relevant | low | YES |
| G-20 | not_relevant | - | not_relevant | not_relevant | low | YES |
| G-21 | not_relevant | - | not_relevant | not_relevant | low | YES |
| G-22 | not_relevant | - | not_relevant | not_relevant | low | YES |
| G-23 | not_relevant | - | relevant | product_comparison | medium | no |
| G-24 | relevant | review_checking | relevant | review_checking | high | YES |
