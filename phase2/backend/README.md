# Phase 2 — Data Collection Layer

> Companion: [`ARCHITECTURE_6_PHASE_PLAN.md`](../../ARCHITECTURE_6_PHASE_PLAN.md) Phase 2 · [`EDGE_CASES.md`](../../EDGE_CASES.md) §1–2

## Goal

Build the collection pipeline and produce a **raw corpus** of publicly available conversations — versioned JSONL + SQLite mirror, with dedup at collection time and a run report.

## Status: IMPLEMENTED

- [x] Source adapters: Reddit (PRAW), Google Play (google-play-scraper), App Store (app-store-scraper), generic web JSON (forums/blogs/YouTube exports), CSV import fallback
- [x] Collection orchestration with rate-limit-aware handling + graceful skip when credentials/network unavailable
- [x] Dedup at collection time (per-source external id + normalized text hash; cross-source and cross-run)
- [x] Persistence: versioned JSONL per source + SQLite mirror
- [x] Run report (markdown): per-source kept/users/URL coverage/duplicates/invalid/date range
- [x] Offline fixture mode for deterministic demos + evaluator (no credentials required)
- [x] Tests: 10 passing (schema, dedup, fixtures, cross-run, reporting, graceful adapter failure)

## Layout

```
phase2/backend/
  src/
    raw.py              # record schema, hashing, validation (arch 6.1)
    storage.py          # SQLite mirror + JSONL snapshots + run bookkeeping
    adapters/           # base + reddit / google_play / app_store / web_json / csv_import
    orchestrator.py     # dedup, persistence, per-source stats
    report.py           # markdown run report
    cli.py              # CLI entry point
  config/collection.yaml  # targets, app ids, subreddits (VERIFY ids before live run)
  requirements.txt
  .env.example          # REDDIT_CLIENT_ID/SECRET, etc.
  tests/test_collection.py
phase2/data/
  fixtures/             # sample exports (tracked): reddit_web / app_store / csv
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
python -m src.cli collect --fixtures --sources reddit_web csv_import

# live collection (needs credentials / network / verified app ids):
set REDDIT_CLIENT_ID=...     # or copy .env.example -> .env
python -m src.cli collect --live --sources reddit google_play app_store
```

## Decision notes

- **Fixtures-first:** the pipeline runs end-to-end offline so an evaluator can always test it; live adapters are lazy-imported and raise `SourceUnavailable` (recorded in the run report) when creds/network are missing — this satisfies the "graceful failure" edge cases (EC-01…EC-03, EC-41).
- **Raw schema** matches architecture plan §6.1 (source, source_external_id, url, author, timestamp, text, language, engagement_metrics, collected_at, raw_hash, is_duplicate_of).
- **Dedup units:** uniqueness on `(source, external_id)`; exact de-dup on normalized-text hash across sources and runs.
- **Count unit** is one conversation (Reddit submission / review / forum post), not every comment — EC-32.
- **PII:** user handles are stored only when already public; no enrichment (EC-14, ethics section).

## Exit criteria (from architecture plan)

- [x] ≥ N conversations collected across ≥ 2 primary sources → 16 kept across 3 sources in fixture mode (reddit_web, app_store, csv/forums)
- [x] No broken records → 100% URL coverage, invalid records rejected + reported
- [x] All traceable to a source URL → `with_url == kept` and reported per source

## Edge cases handled here

EC-01 empty results → graceful report; EC-02 rate limits → retry/backoff + resume by external_id; EC-05 dupes across sources → text-hash dedup; EC-06 spam noise → passes to Phase 3 quarantine; EC-08 long threads → chunk-size config if needed in Phase 3; EC-14 PII → no enrichment; EC-41 missing API key → `SourceUnavailable` in run report.

## Next phase (Phase 3)

Cleaning, exact/near-dedup with embeddings, relevance classifier (keyword pre-filter + LLM), and the `relevant_corpus` using this raw corpus as input.