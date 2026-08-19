# Phase 3 — Cleaning, Deduplication & Relevance Filtering

> Working Principle (keep at top of all working documents):
> Don't build the solution I think is right. Build the discovery system that helps me find the problem worth solving.
>
> Companions: [`ARCHITECTURE_6_PHASE_PLAN.md`](../../ARCHITECTURE_6_PHASE_PLAN.md) §4 Phase 3, [`EDGE_CASES.md`](../../EDGE_CASES.md) §2–3.

Produces the **relevant corpus** — only conversations that talk about wishlist
behaviour, purchase intention/hesitation, product comparison, fashion
decision-making, fit/size/quality, occasion/gift shopping, review-checking, or
shopping experience. Everything else is quarantined with a reason (never deleted
silently) or flagged as a duplicate.

## Pipeline

```
raw_corpus ─► [clean] ─► [dedup] ─► [relevance] ─► relevant_corpus
                │           │            └─► category + reason + confidence + version
                ▼           ▼
            quarantine  duplicates flagged
          (spam/promo/   (exact + near,
          non-Latin/      is_duplicate_of)
          too-short)
```

- **Cleaning** (`src/cleaning.py`): normalize (NFKC + whitespace/quotes),
  PII-mask (email/phone/order-id, EC-14), quarantine spam/promo/bot-gibberish
  (EC-06/13), out-of-scope non-Latin script (EC-04), sub-10-char hollow reviews
  (EC-07).
- **Dedup** (`src/dedup.py`): exact duplicate by normalized-text hash + near
  duplicate by 4-gram Jaccard shingles (≥ 0.82). Representative stays; the rest
  are marked `is_duplicate_of` (EC-10/11). Optional ChromaDB/embedding path can
  be slotted in as an `Embedder` without touching the pipeline.
- **Relevance** (`src/relevance.py` + `src/llm.py`): keyword rules pre-scored
  against the Phase 1 taxonomies; if `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` is
  present the **LLM is the decision-maker** (EC-18), otherwise rules decide and
  the run is fully offline (EC-39/41). Every row records `relevance_category`,
  `relevance_reason`, `relevance_confidence`, `decision_source`, and pinned
  `classifier_version` (EC-42/43).

## Accuracy on the golden set

Golden set: `data/golden_set/relevance_golden.jsonl` (24 hand-labelled
conversations, including the tricky EC cases: wish-verb vs wishlist [EC-15],
song-playlist gate [EC-50], instant-purchase success [EC-46/47], post-purchase
returns [EC-49], Hinglish, non-Latin, spam, gibberish).

Deterministic rule baseline (`rules-v1.0`, offline, no API key needed):

| Class | Precision | Recall | F1 |
|-------|-----------|--------|----|
| relevant | 0.94 | 1.00 | 0.97 |
| not_relevant | 1.00 | 0.88 | 0.93 |

Agreement vs human labels: **23/24 = 95.8%** (single miss: non-fashion product
comparison, EC-50 — expected, LLM gate fixes it at scale). Architecture target:
≥ 85%.

## Run it

```bash
cd phase3/backend
python -m pip install -r requirements.txt

# 1. run the funnel on the fixture corpus (offline, deterministic)
python -m src.cli run            # writes data/output/*.jsonl + funnel_report.md + sqlite

# 2. classifier accuracy vs golden set
python -m src.cli accuracy       # writes accuracy_report.md

# 3. summaries
python -m src.cli report

# real corpus: point --input at a phase2 raw JSONL snapshot
python -m src.cli run --input ../phase2/data/raw/reddit_web__20260819-*.jsonl
```

Optional LLM classifier — copy `.env.example` → `.env`, set `ANTHROPIC_API_KEY`
(or `OPENAI_API_KEY`), re-run. Reports then show `decision_source=llm` and
`classifier_version` pinned to the model.

## Layout

```
phase3/
  backend/
    src/
      cleaning.py    # normalize, PII-mask, quarantine rules
      dedup.py       # exact hash + MinHash shingle near-dup
      relevance.py   # keyword-rule scorer + LLM-structured decision
      llm.py         # optional Claude/GPT provider (offline fallback)
      pipeline.py    # raw -> clean -> dedup -> relevance + funnel stats
      storage.py     # SQLite mirror + JSONL corpora + run bookkeeping
      evaluator.py   # golden-set precision/recall/F1/agreement
      report.py      # funnel report + accuracy report (markdown)
      cli.py
      config.py      # loads relevance.yaml + .env
    config/relevance.yaml   # categories, keyword signals, spam rules
    tests/test_phase3.py    # 15 tests
  data/
    fixtures/raw_sample.jsonl        # 30-record mixed corpus (tracked)
    golden_set/relevance_golden.jsonl# 24 hand-labelled items (tracked)
    output/                          # regenerated (ignored except *.md)
```

## Exit criteria (from architecture)

- [x] clean, deduplicated corpus with **relevance category** on every kept row
- [x] accuracy documented on the golden set (≥ 85% target → 95.8% rule baseline)
- [x] filtering funnel stats recorded per run
- [x] grace under EC-04/06/07/10/11/13/14/15/18/39/41/42/43/47/49/50

## Edge cases handled here

EC-04 keep language tag · EC-06 spam → quarantine · EC-07 hollow/too-short →
quarantine · EC-10 exact dup · EC-11 near dup via shingles · EC-13 promo
pre-filter · EC-14 PII mask · EC-15 wish-verb vs wishlist · EC-18 LLM not gated
by keywords · EC-39/41 offline + missing-key grace · EC-42/43 version pinning ·
EC-47/49 not treated as barriers · EC-50 fashion+shopping gate.