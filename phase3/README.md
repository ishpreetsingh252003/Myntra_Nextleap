# Phase 3 — Cleaning, Deduplication & Relevance Filtering

Placeholder. Build target (see `ARCHITECTURE_6_PHASE_PLAN.md` Phase 3):

- Cleaning transforms: text normalization, exact + near-dedup (embeddings), spam/bot/ad removal.
- Relevance classifier (keyword pre-filter + LLM) with `relevant / not_relevant` + category.
- Filtering funnel stats (collected → cleaned → relevant).
- Golden set: `../phase1/data/golden_set/golden_relevance_*.json` (20–30 items).

Exit: relevant corpus clean, deduped, tagged; classifier accuracy ≥ 85% agreement on golden set.