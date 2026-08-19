# Phase 2 — Data Collection Layer

> Companion: [`ARCHITECTURE_6_PHASE_PLAN.md`](../../ARCHITECTURE_6_PHASE_PLAN.md) Phase 2 · [`EDGE_CASES.md`](../../EDGE_CASES.md) §1–2

## Goal

Build the collection pipeline and produce a **raw corpus** of publicly available conversations — versioned JSONL + SQLite mirror, with dedup at collection time and a run report.

## Status: IMPLEMENTED

- [x] Source adapters: Reddit (PRAW), Google Play, App Store, YouTube (Data API v3), Quora (best-effort), web JSON (forums/blogs/product-reviews/Amazon exports), CSV import fallback
- [x] Collection orchestration with rate-limit-aware handling + graceful skip when credentials/network unavailable
- [x] Dedup at collection time (per-source external id + normalized text hash; cross-source and cross-run)
- [x] Persistence: versioned JSONL per source + SQLite mirror
- [x] Run report (markdown): per-source kept/users/URL coverage/duplicates/invalid/date range
- [x] Offline fixture mode for deterministic demos + evaluator (no credentials required); covers **9 sources**
- [x] Tests: 11 passing (schema, dedup, all-sources coverage, fixtures, cross-run, reporting, graceful adapter failure)

## Source coverage

| Source | Live adapter | Credentials | Offline fixture |
|--------|--------------|-------------|-----------------|
| Google Play reviews | `google_play` | none (network) | `google_play_sample.json` |
| Apple App Store reviews | `app_store` | none (network) | `app_store_sample.json` |
| Reddit | `reddit` (PRAW) | free Reddit app | `reddit_web_sample.json` |
| YouTube comments | `youtube_comments` | free API key | `youtube_comments_sample.json` |
| Quora | `quora` (best-effort) | none | `quora_sample.json` |
| Forums / blogs | export → `web_json` | — | `forums_blogs_sample.json` |
| On-platform product reviews (Myntra/Nykaa/AJIO) | export → `web_json` | ToS-check | `product_reviews_sample.json` |
| Amazon.in reviews | export → `web_json` | ToS-check | `amazon_sample.json` |
| CSV upload fallback | `csv_import` | — | `csv_import_sample.csv` |

`product_reviews`/`amazon` live content is fetched manually/exported (their public
review endpoints are unofficial and ToS-restricted) and ingested via `web_json`
`custom` schema. Fixture mode collects **all 9 sources** in one run.

## Layout

```
phase2/backend/
  src/
    raw.py              # record schema, hashing, validation (arch 6.1)
    storage.py          # SQLite mirror + JSONL snapshots + run bookkeeping
    adapters/           # base + reddit / google_play / app_store / youtube / quora / web_json / csv_import
    orchestrator.py     # dedup, persistence, per-source stats
    report.py           # markdown run report
    cli.py              # CLI entry point
  config/collection.yaml  # targets, app ids, subreddits, YT queries (VERIFY ids before live run)
  requirements.txt
  .env.example          # REDDIT_CLIENT_ID/SECRET, YOUTUBE_API_KEY, etc.
  tests/test_collection.py
phase2/data/
  fixtures/             # sample exports (tracked): 8 JSON/CSV files for 9 sources
  raw/                  # JSONL snapshots (gitignored)
  db/                   # corpus.sqlite3 (gitignored)
  reports/latest.md     # latest run report
```

## How to run

```bash
cd phase2/backend
python -m pip install -r requirements.txt

# offline demo (deterministic, no credentials):
python -m src.cli collect --fixtures
python -m src.cli collect --fixtures --sources reddit_web google_play youtube_comments

# live collection (needs credentials / network / verified app ids):
set REDDIT_CLIENT_ID=...     # or copy .env.example -> .env
set YOUTUBE_API_KEY=...
python -m src.cli collect --live --sources reddit google_play app_store youtube_comments quora
```

## Decision notes

- **Fixtures-first:** the pipeline runs end-to-end offline so an evaluator can always test it; live adapters are lazy-imported and raise `SourceUnavailable` (recorded in the run report) when creds/network are missing — this satisfies the "graceful failure" edge cases (EC-01…EC-03, EC-41).
- **Raw schema** matches architecture plan §6.1 (source, source_external_id, url, author, timestamp, text, language, engagement_metrics, collected_at, raw_hash, is_duplicate_of).
- **Dedup units:** uniqueness on `(source, external_id)`; exact de-dup on normalized-text hash across sources and runs.
- **Count unit** is one conversation (Reddit submission / review / forum post), not every comment — EC-32.
- **PII:** user handles are stored only when already public; no enrichment (EC-14, ethics section).

## Exit criteria (from architecture plan)

- [x] ≥ N conversations collected across ≥ 2 primary sources → 39 kept across **9 sources** in fixture mode
- [x] No broken records → 100% URL coverage, invalid records rejected + reported
- [x] All traceable to a source URL → `with_url == kept` and reported per source

## Edge cases handled here

EC-01 empty results → graceful report; EC-02 rate limits → retry/backoff + resume by external_id; EC-05 dupes across sources → text-hash dedup; EC-06 spam noise → passes to Phase 3 quarantine; EC-08 long threads → chunk-size config if needed in Phase 3; EC-14 PII → no enrichment; EC-31 source-bias tracking → per-source reporting built in; EC-41 missing API key → `SourceUnavailable` per adapter in run report (YT/Reddit/Quora all covered).

## Next phase (Phase 3)

Cleaning, exact/near-dedup with embeddings, relevance classifier (keyword pre-filter + LLM), and the `relevant_corpus` using this raw corpus as input.