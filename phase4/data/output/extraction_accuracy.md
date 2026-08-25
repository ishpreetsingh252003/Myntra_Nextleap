# Phase 4 Extraction Accuracy Report

- **Generated:** 2026-08-26T02:41:21
- **Golden set size:** 20
- **Extractor version:** extraction-v1.0
- **Decision source:** rules (offline baseline)

Architecture target: ≥ 80% agreement vs human labels.

## Extraction quality

| Metric | Score |
|--------|-------|
| Behaviour F1 (avg) | 0.66 |
| Barrier F1 (avg) | 0.598 |
| **Overall agreement** | **0.629** |
| Three-level pass rate | 1.0 |
| Quote valid rate | 0.0 |
| Intent accuracy | 0.8 |

## Per-packet breakdown

| id | gold_beh | pred_beh | beh_f1 | gold_bar | pred_bar | bar_f1 | 3L | quote | intent |
|----|----------|----------|--------|----------|----------|--------|-----|-------|--------|
| EP-G01 | shortlist_products,bookmark_for_later | shortlist_products | 0.667 | forgetting | forgetting | 1.0 | ok | MISS | ok |
| EP-G02 | wait_before_buying,price_track | wait_before_buying,price_track | 1.0 | price_uncertainty | price_uncertainty | 1.0 | ok | MISS | ok |
| EP-G03 | compare_products,check_fit | compare_products,check_fit | 1.0 | comparison_bloat,fit_uncertainty | fit_uncertainty | 0.667 | ok | MISS | ok |
| EP-G04 | check_fit,shortlist_products | shortlist_products,check_fit | 1.0 | size_uncertainty,fit_uncertainty | fit_uncertainty,size_uncertainty | 1.0 | ok | MISS | ok |
| EP-G05 | shop_for_occasion,check_reviews,shortlist_products | check_quality,shop_for_occasion | 0.4 | reality_uncertainty,review_doubt | none_stated | 0.0 | ok | MISS | ok |
| EP-G06 | check_reviews | - | 0.0 | review_doubt | none_stated | 0.0 | ok | MISS | MISS |
| EP-G07 | wait_before_buying,price_track | wait_before_buying,price_track | 1.0 | price_uncertainty | price_uncertainty | 1.0 | ok | MISS | ok |
| EP-G08 | compare_products,seek_social_validation,wait_before_buying | seek_social_validation,price_track | 0.4 | comparison_bloat,price_uncertainty | price_uncertainty | 0.667 | ok | MISS | MISS |
| EP-G09 | gift_shopping,compare_products,shortlist_products | shortlist_products,shop_for_occasion,gift_shopping | 0.667 | comparison_bloat | none_stated | 0.0 | ok | MISS | ok |
| EP-G10 | check_reviews | - | 0.0 | delivery_concern,return_concern | delivery_concern,return_concern | 1.0 | ok | MISS | ok |
| EP-G11 | check_fit,shortlist_products | shortlist_products,wait_before_buying | 0.5 | size_uncertainty | size_uncertainty | 1.0 | ok | MISS | ok |
| EP-G12 | check_fit | check_fit | 1.0 | fit_uncertainty,return_concern | fit_uncertainty,return_concern | 1.0 | ok | MISS | MISS |
| EP-G13 | check_quality,check_reviews | check_quality | 0.667 | reality_uncertainty,quality_uncertainty | quality_uncertainty,reality_uncertainty,authenticity_concern | 0.8 | ok | MISS | ok |
| EP-G14 | shortlist_products | shortlist_products | 1.0 | none_stated | none_stated | 1.0 | ok | MISS | ok |
| EP-G15 | compare_products,check_fit,check_reviews | compare_products | 0.5 | fit_uncertainty,comparison_bloat | comparison_bloat | 0.667 | ok | MISS | ok |
| EP-G16 | wait_before_buying,shortlist_products,price_track | shortlist_products,wait_before_buying,price_track | 1.0 | price_uncertainty | none_stated | 0.0 | ok | MISS | ok |
| EP-G17 | wait_before_buying,shortlist_products,price_track | shortlist_products,wait_before_buying,price_track | 1.0 | price_uncertainty | none_stated | 0.0 | ok | MISS | ok |
| EP-G18 | check_quality | check_quality | 1.0 | quality_uncertainty,reality_uncertainty | quality_uncertainty,authenticity_concern | 0.5 | ok | MISS | ok |
| EP-G19 | shortlist_products,check_fit | - | 0.0 | size_uncertainty,fit_uncertainty | size_uncertainty | 0.667 | ok | MISS | MISS |
| EP-G20 | shop_for_occasion,check_reviews,compare_products | shop_for_occasion,self_shopping | 0.4 | review_doubt | none_stated | 0.0 | ok | MISS | ok |
