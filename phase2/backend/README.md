# Phase 2 — Data Collection Layer

Placeholder. Build target (see `ARCHITECTURE_6_PHASE_PLAN.md` Phase 2):

- Source adapters in `phase2/backend`: PRAW (Reddit), google-play-scraper, app-store-scraper.
- Collection orchestration, rate-limit awareness, dedup at collection time.
- Raw corpus → `data/raw/*.jsonl` + SQLite mirror + collection run report.

Deliverables: collection scripts, source config, raw dataset with metadata, run report.
Exit: ≥ N conversations across ≥ 2 primary sources, all traceable to source URLs.