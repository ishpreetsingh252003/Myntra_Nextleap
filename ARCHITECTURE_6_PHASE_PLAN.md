# Architecture Plan — AI-Powered Fashion Wishlist Discovery Engine (6 Phases)

> **Working Principle (keep at top of all working documents):**
> Don't build the solution I think is right. Build the discovery system that helps me find the problem worth solving.
>
> Companion doc: [problemstatementbrief.md](problemstatementbrief.md)

---

## Table of Contents

1. [Solution Overview](#1-solution-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Phase-Wise Plan (6 Phases)](#4-phase-wise-plan-6-phases)
5. [Cross-Cutting Concerns](#5-cross-cutting-concerns)
6. [Data & Evidence Model](#6-data--evidence-model)
7. [Testing & Evaluation Strategy](#7-testing--evaluation-strategy)
8. [Risk Register & Mitigations](#8-risk-register--mitigations)
9. [Success Criteria](#9-success-criteria)
10. [Open Questions for Evaluator / Mentor](#10-open-questions-for-evaluator--mentor)

---

## 1. Solution Overview

The Discovery Engine is a **research/analysis system** (not a user-facing app) composed of:

1. **Collection Layer** — pulls public conversations from App Store, Google Play Store, Reddit, and optionally YouTube comments, forums, and public blogs.
2. **Processing Layer** — cleaning, deduplication, spam removal, relevance classification.
3. **AI Extraction Layer** — behaviour extraction, barrier extraction, unmet-need inference, segment classification.
4. **Analysis Layer** — theme clustering, quantification, opportunity scoring.
5. **Evidence Database** — every insight traceable to raw quotes, source, frequency, confidence.
6. **Discovery Dashboard / Report** — testable workflow: input a research question → see analysed conversations, behaviours, barriers, segments, opportunities, evidence, and interview questions.

### Key Design Principles

- **Evidence over volume:** Every insight must be traceable to actual user quotes. Frequency of mention ≠ business impact.
- **Three-level distinction (never conflated):** said → inferred → concluded.
- **Segments emerge from data**, not from assumptions.
- **Engine assists the PM** — it never decides the final solution.
- **Testable end-to-end:** evaluator can enter a research question, run the workflow, and inspect outputs.

---

## 2. High-Level Architecture

### 2.1 Logical Pipeline

```
Data Sources (App Store, Play Store, Reddit, forums, comments)
        │
        ▼
[1] Collection Layer ──► raw_corpus (source, url, text, metadata)
        │
        ▼
[2] Cleaning & Deduplication ──► clean_corpus (spam/bot/ads removed)
        │
        ▼
[3] Relevance Classifier ──► relevant_corpus (wishlist/purchase/hesitation/comparison...)
        │
        ▼
[4] Behaviour Extraction ──► behaviour records (what user was trying to do)
        │
        ▼
[5] Barrier Extraction ──► barrier records (what blocked them)
        │
        ▼
[6] Unmet-Need Inference ──► unmet_need records (what was missing)
        │
        ▼
[7] Segment Classification ──► segment assignments
        │
        ▼
[8] Theme Clustering + Quantification ──► counts, %, per-source, per-segment
        │
        ▼
[9] Opportunity Scoring ──► ranked opportunity areas
        │
        ▼
[10] Evidence Database ──► every insight linked to quotes + confidence
        │
        ▼
[11] Discovery Dashboard / Report (testable workflow)
```

### 2.2 Component Responsibilities

- **Source Adapters:** one adapter per source, normalizing data into a common schema (`source, external_id, url, text, author, timestamp, engagement_metrics`).
- **Relevance Classifier:** LLM + keyword hybrid; tags conversations relevant/not relevant; reasons stored.
- **Extractors:** structured JSON per conversation → intent, behaviours (multi-label), barriers (multi-label), unmet needs, user role (self/other), confidence.
- **Segment Engine:** rule + embedding clustering to assign segments.
- **Opportunity Scorer:** weighted formula over frequency, severity, purchase impact, evidence strength, segment concentration, existing workarounds, product leverage.

---

## 3. Tech Stack

| Layer | Tools |
|-------|-------|
| Language / testing | Python 3.11+, `pytest` |
| LLM / AI | Claude API (alternate: GPT API) |
| Collection | PRAW (Reddit), google-play-scraper, app-store-scraper |
| Storage | JSONL datasets + SQLite |
| Vector store | ChromaDB |
| Clustering / analysis | Embeddings (Claude/OpenAI), `scikit-learn`/`hdbscan`, `pandas` |
| Dashboard / report | Streamlit; Markdown/HTML reports |

> Specific package choices will be finalized inside each phase.

---

## 4. Phase-Wise Plan (6 Phases)

Each phase is a **vertical slice** with: goal, tech stack, tasks, inputs/outputs, deliverables, and exit criteria.

---

### Phase 1 — Discovery Foundation & Problem Framing

**Goal:** Turn the business question into a testable research instrument and define the evidence model *before* touching data.

**Tech Stack:** Python 3.11+, `pytest`, `.env` for API keys, Claude/GPT API.

**Tasks:**
- [ ] Write the working principle and problem statement (`problemstatementbrief.md`).
- [ ] Decompose the core research question into sub-questions.
- [ ] Define the initial hypothesis library (wishlist intent + purchase barriers).
- [ ] Define the **behaviour taxonomy skeleton** (shortlist, compare, wait, check fit, check quality, seek social validation, occasion shopping, bookmark, etc.).
- [ ] Define the **evidence schema** (see Section 6).
- [ ] Define the **three-level distinction** template (quote → inference → conclusion).
- [ ] Select data sources and confirm public-access terms.
- [ ] Define candidate segmentation dimensions (to be validated later against data).
- [ ] Scaffold repository: `data/`, `scripts/`, `config/`, `notebooks/`, `docs/`, `tests/`.
- [ ] Define the golden test set strategy (20–30 hand-labelled conversations per classifier/extractor).

**Inputs:** problem statement brief.
**Outputs:** taxonomies, evidence schema, repo scaffold, golden-set plan.

**Deliverables:** problem framing doc, evidence schema + taxonomy skeleton, golden-set labelling guide, repository scaffold.

**Exit Criteria:** a new evaluator reading Phase 1 outputs can independently answer "what are we researching and how will we know what counts as evidence?"

---

### Phase 2 — Data Collection Layer

**Goal:** Build the collection pipeline and produce a real, raw corpus of publicly available conversations.

**Tech Stack:** Python scrapers — PRAW (Reddit), google-play-scraper, app-store-scraper; JSONL + SQLite storage.

**Tasks:**
- [ ] Build **source adapters** per source:
  - App Store reviews (iOS).
  - Google Play Store reviews.
  - Reddit — fashion/shopping subreddits + search for Myntra, AJIO, Nykaa Fashion, online fashion shopping discussions.
  - Optional: YouTube comments, fashion forums, public blogs/community threads.
- [ ] Implement **collection orchestration** (manual/scheduled run, rate-limit aware).
- [ ] Implement **dedup at collection time** (external_id, url, text hash).
- [ ] Persist raw corpus as versioned JSONL + DB records with full metadata.
- [ ] Store source/URL ethics + attribution metadata (compliance & traceability).
- [ ] Log collection statistics (per-source counts, date ranges).

**Inputs:** source list (Phase 1), target volume budget.
**Outputs:** `raw_corpus` dataset.

**Deliverables:** collection scripts, source config, raw dataset with metadata, collection run report.

**Exit Criteria:** ≥ N genuine conversations collected across ≥ 2 primary sources, no broken records, all traceable to a source URL.

---

### Phase 3 — Cleaning, Deduplication & Relevance Filtering

**Goal:** Produce a high-quality **relevant corpus** — only conversations that talk about wishlist behaviour, purchase intention/hesitation, product comparison, fashion decision-making, uncertainty, or shopping behaviour.

**Tech Stack:** `pandas` for cleaning; LLM relevance classifier (Claude/GPT) + embedding-based dedup.

**Tasks:**
- [ ] Implement cleaning transforms: normalize text, remove duplicates (exact + near-dup via embeddings), remove spam/bots/ads, filter out-of-scope language.
- [ ] Implement **Relevance Classifier** (keyword rules + LLM with structured output): labels `relevant / not_relevant` + `relevance_category`.
- [ ] Human review pass on a sample vs golden set (target ≥ 85% agreement).
- [ ] Log filtering funnel stats (collected → cleaned → relevant).

**Inputs:** raw_corpus (Phase 2).
**Outputs:** `clean_corpus`, `relevant_corpus` + funnel stats.

**Deliverables:** cleaning + classifier scripts, filtering report, classifier accuracy report.

**Exit Criteria:** relevant corpus is clean, deduplicated, tagged with relevance category; accuracy documented on the golden set.

---

### Phase 4 — Behaviour, Barrier & Unmet-Need Extraction

**Goal:** Convert relevant conversations into structured, evidence-linked insight records — the heart of the Discovery Engine.

**Tech Stack:** LLM extraction (Claude/GPT) with structured JSON (`pydantic`); embeddings + ChromaDB.

**Tasks:**
- [ ] Build **Behaviour Extractor** (multi-label): what the user was trying to do (shortlist, compare, wait, check fit/quality, seek social validation, occasion shopping, remember for later, price-check, gift/self-shopping); user role; funnel stage.
- [ ] Build **Barrier Extractor** (multi-label): map to hypothesis library; capture "why" wording verbatim.
- [ ] Build **Unmet-Need Inference:** what information, confidence, functionality, or experience was missing? Kept distinct from the raw quote.
- [ ] Build the **Evidence Packet** generator per conversation (quote + behaviours + barriers + unmet needs + segment hints + source + confidence).
- [ ] Validate extractors on golden set (target ≥ 80% agreement).
- [ ] Store per-conversation embeddings for later clustering.

**Inputs:** relevant_corpus (Phase 3), taxonomies (Phase 1).
**Outputs:** `extracted_insights` dataset.

**Deliverables:** extractor scripts + prompt configs, extraction accuracy report, sample of 20 fully worked evidence packets.

**Exit Criteria:** a human can read any evidence packet and see exactly (a) the quote, (b) what we inferred, (c) what we conclude — clearly separated.

---

### Phase 5 — Segmentation, Theme Clustering & Quantification

**Goal:** Discover patterns *across* conversations: co-occurring behaviours, user segments, and pattern frequencies.

**Tech Stack:** `scikit-learn`/`hdbscan` for clustering; `pandas` for quantification tables.

**Tasks:**
- [ ] **Segment Classification:** derive segments from data (first-time/frequent shoppers, high-wishlist users, occasion-based, self/others, budget/fashion-conscious, comparers, repeated sizing concerns) — test against data, don't assume.
- [ ] **Theme Clustering:** cluster evidence packets by behaviour+barrier vectors; extract labels.
- [ ] **Quantification:** counts per theme, users per barrier/behaviour, % of relevant conversations, frequency by source and segment, behaviour co-occurrence matrices.
- [ ] **Impact-Weighted Reporting:** clearly separate frequency of mention from evidence of business impact.
- [ ] Validate clusters/segments on the golden set + human sanity check.

**Inputs:** extracted_insights (Phase 4).
**Outputs:** segment assignments, theme clusters, quantification tables.

**Deliverables:** clustering scripts, segment/theme reports, quantification tables (CSV), co-occurrence analysis.

**Exit Criteria:** every segment and theme is traceable to ≥ 3 evidence packets; frequency tables exist per source and segment.

---

### Phase 6 — Opportunity Ranking, Evidence DB & Discovery Dashboard

**Goal:** Turn analysed data into a **PM decision tool**: ranked opportunities, browsable evidence database, testable end-to-end workflow.

**Tech Stack:** Streamlit dashboard; SQLite evidence DB; reports as Markdown/HTML.

**Tasks:**
- [ ] Build **Opportunity Scorer** (weighted dimensions — see Section 5.1) with transparent score breakdown.
- [ ] Build **Evidence Database** linking each opportunity/theme/barrier → evidence packets → quotes → source URL; store confidence.
- [ ] Build **Discovery Dashboard** (Streamlit): research-question input → top barriers, segments, behaviour patterns, frequencies, supporting quotes, opportunity ranking, three-level distinctions.
- [ ] Build **Interview Question Generator:** 2–3 open-ended questions per ranked opportunity (for the 5–6 primary interviews).
- [ ] Write the final **Discovery Report** (evidence DB, behaviour + barrier taxonomies, segments, ranked opportunities, evidence per opportunity, interview questions).
- [ ] **End-to-end acceptance test** on real data with a fresh research question; capture a run report.

**Inputs:** all Phase 4/5 outputs.
**Outputs:** ranked opportunities, evidence DB, dashboard, interview questions, final report.

**Deliverables:** scorer + dashboard + evidence DB + Discovery Report + run report.

**Exit Criteria:** an evaluator can run the workflow, see analysed conversations, inspect evidence, compare opportunity areas, and read a ranked output with interview questions — fully traceable to raw data.

---

## 5. Cross-Cutting Concerns

### 5.1 Opportunity Scoring Dimensions (weighted)

| Dimension | Weight (example) | Meaning |
|-----------|------------------|---------|
| Frequency | 0.20 | Share of relevant conversations mentioning the theme |
| Severity | 0.15 | How far it blocks the funnel (post-evaluation drop-off vs passive forgetfulness) |
| Purchase impact | 0.20 | Estimated effect on Wishlist → Purchase 30-day conversion |
| Users affected | 0.10 | Size of segment concentration |
| Evidence strength | 0.15 | Quality/consistency of quotes, extraction confidence |
| Segment concentration | 0.05 | Concentration in a targetable segment |
| Existing workaround | 0.10 | Are users solving it elsewhere (e.g., comparing on other apps)? |
| Product leverage | 0.05 | Feasibility of a product intervention |

Weights are a starting point and must be justified in the report.

### 5.2 Evidence & Confidence Tiers

- **High:** multiple independent users, consistent language, direct behavioural description.
- **Medium:** recurring theme but indirect language or single-source concentration.
- **Low:** anecdotal, ambiguous, or single mention.

### 5.3 Ethics & Compliance

- Only publicly available data; respect platform ToS and API rate limits.
- Never publish personal data beyond what is public; no PII enrichment.
- Attribute sources for traceability.
- If platform terms restrict scraping, switch to supported APIs or documented manual exports.

---

## 6. Data & Evidence Model

### 6.1 Conversation (raw)
```
id, source, source_external_id, url, author, timestamp,
text, language, engagement_metrics, collected_at, raw_hash, is_duplicate_of
```

### 6.2 Relevant Conversation
```
conversation_id, relevance_category, relevance_reason, classifier_version
```

### 6.3 Evidence Packet (extracted)
```
conversation_id, quote (verbatim), quote_char_start/end,
intent (purchase / bookmark / save-for-later / occasion / gift / unknown),
behaviours [multi-label], barriers [multi-label], unmet_needs [multi-label],
user_role (self / other / unknown), funnel_stage,
segment_hints [multi-label], confidence (per label), extractor_version
```

### 6.4 Insight (analysed)
```
insight_id, theme, behaviour_pattern, barrier, segment,
evidence_packet_ids [], source_frequency, percentage_of_relevant,
evidence_strength, confidence, notes
```

### 6.5 Opportunity
```
opportunity_id, title, behaviour, barrier, segment,
score, score_breakdown (per dimension), supporting_evidence_ids [],
existing_workarounds, product_leverage_notes, proposed_interview_questions []
```

---

## 7. Testing & Evaluation Strategy

- **Golden set:** 20–30 hand-labelled conversations per classifier/extractor, fixed before tuning.
- **Accuracy metrics:** precision/recall/agreement for relevance classifier and each extractor label.
- **E2E acceptance test:** fresh research question → full pipeline → inspect outputs.
- **Negative tests:** spam-only input, non-English input, empty corpus → pipeline fails gracefully.
- **Reproducibility:** datasets versioned; runs recorded with config + model versions + timestamps.

---

## 8. Risk Register & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Insufficient relevant data in sources | High | Source expansion list (YouTube, forums, blogs); broad subreddit search |
| Classifier/extractor accuracy too low | High | Golden-set-driven iteration; human review sample; confidence labels |
| Platform ToS / scraping limits | Medium | Prefer official APIs; fallback to manual exports; documented approach |
| LLM cost at scale | Medium | Batch + caching; stratified sampling before full-run |
| Frequency ≠ impact confusion | Medium | Impact-weighted scoring + funnel-stage tagging baked in |
| Evaluator can't reproduce run | Medium | Versioned data, run config, one-command pipeline, run report |

---

## 9. Success Criteria

The Discovery Engine is successful if, after using it, we can confidently say:

> "I started with an unknown wishlist-to-purchase problem. I analyzed user conversations at scale, identified recurring behaviours and barriers, quantified the strongest patterns where possible, compared opportunity areas, and now know which problem I should validate with real users."

### Phase-end success checklist (final report must contain)

- [ ] **A. Evidence database**
- [ ] **B. Behaviour taxonomy**
- [ ] **C. Barrier taxonomy**
- [ ] **D. User segments**
- [ ] **E. Opportunity areas** (ranked)
- [ ] **F. Evidence per opportunity**
- [ ] **G. Interview research questions** (for 5–6 interviews)

---

## 10. Open Questions for Evaluator / Mentor

1. Are app-store review collections (via public feeds) preferred over scraped HTML? Compliance constraints?
2. Which Reddit / community sources are acceptable?
3. Is a Python + SQLite + ChromaDB stack acceptable, or is a specific AI stack required?
4. Minimum corpus volume expectation (e.g., "1,000+ relevant conversations")?
5. Should the dashboard be a runnable app (Streamlit) or a static report for evaluation?

---

*Working draft — to be evolved as evidence is collected.*