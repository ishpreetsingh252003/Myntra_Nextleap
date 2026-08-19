# NextLeap Graduation Project — AI-Powered Fashion Wishlist Discovery Engine

> **Working Principle (keep at top of all working documents):**
> Don't build the solution I think is right. Build the discovery system that helps me find the problem worth solving.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Business Context & Goal](#2-business-context--goal)
3. [Core Research Question](#3-core-research-question)
4. [Solution Overview](#4-solution-overview)
5. [High-Level Architecture](#5-high-level-architecture)
6. [Phase-Wise Plan (6 Phases)](#6-phase-wise-plan-6-phases)
   - [Phase 1 — Discovery Foundation & Problem Framing](#phase-1--discovery-foundation--problem-framing)
   - [Phase 2 — Data Collection Layer](#phase-2--data-collection-layer)
   - [Phase 3 — Cleaning, Deduplication & Relevance Filtering](#phase-3--cleaning-deduplication--relevance-filtering)
   - [Phase 4 — Behaviour, Barrier & Unmet-Need Extraction](#phase-4--behaviour-barrier--unmet-need-extraction)
   - [Phase 5 — Segmentation, Theme Clustering & Quantification](#phase-5--segmentation-theme-clustering--quantification)
   - [Phase 6 — Opportunity Ranking, Evidence DB & Discovery Dashboard](#phase-6--opportunity-ranking-evidence-db--discovery-dashboard)
7. [Cross-Cutting Concerns](#7-cross-cutting-concerns)
8. [Data & Evidence Model](#8-data--evidence-model)
9. [Testing & Evaluation Strategy](#9-testing--evaluation-strategy)
10. [Risk Register & Mitigations](#10-risk-register--mitigations)
11. [Success Criteria](#11-success-criteria)
12. [Open Questions for Evaluator / Mentor](#12-open-questions-for-evaluator--mentor)

---

## 1. Problem Statement

A fashion e-commerce platform (Myntra) sees that a large share of users who add products to their wishlist never purchase those products within the next 30 days. A wishlist is a strong signal of explicit interest — yet many saved items never convert to purchase.

The business does **not know why**. The underlying user problem is intentionally not given.

We need a **Discovery Engine** — not a solution — that:

- Collects large volumes of **publicly available user conversations** about online fashion shopping.
- Extracts **what users are trying to do**, **what blocks them**, **what uncertainty remains**, and **which unmet needs** represent the strongest product opportunities.
- Connects evidence to the business metric **Wishlist → Purchase within 30 days**.
- Produces a ranked, evidence-backed opportunity map that a PM can take into 5–6 primary user interviews to validate a target problem.

**Explicitly out of scope:** building the final solution, MVP, sentiment dashboards, or review summarization.

---

## 2. Business Context & Goal

- **Team:** Growth Team, Product Manager.
- **Business goal:** Increase the % of users who purchase at least one product from their wishlist within 30 days of adding it.
- **Why it matters:** Wishlist = expressed interest. Understanding the gap between *interest* and *purchase* unlocks the single biggest growth lever in this funnel.
- **North-star metric:** Wishlist → Purchase Conversion Rate (30 days).

**Funnel the engine must reason about:**

```
Wishlist added
    ↓
User still intends to purchase
    ↓
User evaluates product
    ↓
User resolves uncertainty
    ↓
User decides
    ↓
Purchase (within 30 days)
```

The engine must identify **where in this chain users get stuck** — not just "users don't buy wishlist products."

---

## 3. Core Research Question

> **Why does a user who has explicitly wishlisted a fashion product not purchase it within the next 30 days?**

### 3.1 Sub-Questions — Wishlist Intent

| ID | Question |
|----|----------|
| WI-1 | Why did the user save the product? |
| WI-2 | Was the wishlist created with an intention to purchase? |
| WI-3 | Was the user simply bookmarking the product? |
| WI-4 | Was the product saved "for later"? |
| WI-5 | Was the user waiting for an occasion? |
| WI-6 | Was the user comparing it with alternatives? |
| WI-7 | Was the user saving multiple similar products? |

### 3.2 Sub-Questions — Purchase Barriers (Hypotheses, not findings)

| ID | Barrier Hypothesis |
|----|--------------------|
| PB-1 | Uncertainty about fit |
| PB-2 | Uncertainty about size |
| PB-3 | Uncertainty about quality |
| PB-4 | Uncertainty about how it looks in reality |
| PB-5 | Uncertainty about styling / how to wear it |
| PB-6 | Uncertainty about occasion suitability |
| PB-7 | Uncertainty about reviews |
| PB-8 | Uncertainty about authenticity |
| PB-9 | Price uncertainty |
| PB-10 | Waiting before spending |
| PB-11 | Comparison with another product |
| PB-12 | Waiting for social validation |
| PB-13 | Product availability |
| PB-14 | Delivery concerns |
| PB-15 | Return / exchange concerns |
| PB-16 | Lack of urgency |
| PB-17 | Simply forgetting about the product |
| PB-18 | Wishlist used as pure bookmarking |

**Important:** these are candidate hypotheses the engine must test against real data. Findings must emerge from evidence — not be confirmed to fit a pre-decided answer.

---

## 4. Solution Overview

The Discovery Engine is a **research/analysis system** (not a user-facing app) composed of:

1. **Collection Layer** — pulls public conversations from App Store, Google Play Store, Reddit, and optionally YouTube comments, fashion forums, and public blogs/communities.
2. **Processing Layer** — cleaning, deduplication, spam removal, relevance classification.
3. **AI Extraction Layer** — behaviour extraction, barrier extraction, unmet-need inference, segment classification.
4. **Analysis Layer** — theme clustering, quantification, opportunity scoring.
5. **Evidence Database** — every insight traceable to raw quotes, source, frequency, confidence.
6. **Discovery Dashboard / Report** — testable workflow: input a research question → see analysed conversations, behaviours, barriers, segments, opportunities, evidence, and interview questions.

### Key Design Principles

- **Evidence over volume:** Every insight must be traceable to actual user quotes. Frequency of mention ≠ business impact.
- **Three-level distinction (never conflated):**
  1. **What users said** (raw quote)
  2. **What we infer** (structured behaviour)
  3. **What we conclude** (barrier / opportunity hypothesis)
- **Segments emerge from data**, not from assumptions.
- **Engine assists the PM** — it never decides the final solution.
- **Testable end-to-end:** evaluator can enter a research question, run the workflow, and inspect the outputs.

---

## 5. High-Level Architecture

### 5.1 Logical Pipeline

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

### 5.2 Recommended Tech Stack (AI-Native, assignment-permitted)

| Layer | Options |
|-------|---------|
| Orchestration | n8n, Python + workflow scripts, Zapier |
| LLM / AI | Claude API, GPT API, Perplexity API (extraction, classification, inference) |
| Embeddings / Vector Store | OpenAI/Claude embeddings + ChromaDB, Pinecone, pgvector, or SQLite-vec |
| Relational DB | SQLite (local, portable), PostgreSQL |
| Storage | JSONL datasets, Parquet, Google Sheets for evidence ledger |
| Collection | Reddit API (PRAW), App Store RSS/API, Play Store scrapers (public), YouTube Data API, community-scraper (where permitted) |
| Dashboard | Streamlit, Gradio, or a static HTML report generator |
| Testing | pytest + golden sets (labelled examples for classifier/extractor accuracy) |

> **Note:** any stack that satisfies the assignment and can be run by the evaluator is acceptable. A concrete, Python-first stack is chosen below and carried through every phase; the dashboard is deployed last.

### 5.3 Component Responsibilities

- **Source Adapters:** one adapter per source, normalizing data into a common schema (`source, external_id, url, text, author, timestamp, engagement_metrics`).
- **Relevance Classifier:** LLM + keyword hybrid; tags conversations as relevant / not relevant; reasons stored.
- **Extractors:** structured JSON output per conversation → intent, behaviours (multi-label), barriers (multi-label), unmet needs, user role (self/other), confidence.
- **Segment Engine:** rule + embedding clustering to assign segments.
- **Opportunity Scorer:** weighted formula over frequency, severity, purchase impact, evidence strength, segment concentration, existing workarounds, product leverage.

---

## 6. Phase-Wise Plan (6 Phases)

Each phase is a **vertical slice** with: objective, tasks, inputs, outputs, deliverables, exit criteria, and testing.

---

### Phase 1 — Discovery Foundation & Problem Framing

**Goal:** Turn the business question into a testable research instrument, and define the evidence model *before* touching data.

**Tech Stack:**
- Python 3.11+; dependency management via `uv` or `requirements.txt`.
- Repo layout: `phase1/`…`phase6/` code, `data/`, `config/`, `notebooks/`, `tests/`, `docs/`.
- Testing harness: `pytest` + golden-set fixtures (JSON).
- LLM access: Claude API key (or OpenAI/GPT) stored in `.env` via `python-dotenv`.

**Tasks:**
- [ ] Write the working principle and problem statement (this document's top).
- [ ] Decompose the core research question into sub-questions (Section 3).
- [ ] Define the initial hypothesis library (wishlist intent + purchase barriers).
- [ ] Define the **behaviour taxonomy skeleton** (shortlist, compare, wait, check fit, check quality, seek social validation, occasion shopping, bookmark, etc.).
- [ ] Define the **evidence schema** (see Section 8).
- [ ] Define the **three-level distinction** template (quote → inference → conclusion) and record it as a project rule.
- [ ] Select data sources and confirm public-access terms (App Store, Play Store, Reddit, optionally YouTube/forums/blogs).
- [ ] Define candidate segmentation dimensions (to be validated later against data).
- [ ] Scaffold repository: `data/`, `scripts/`, `config/`, `notebooks/`, `docs/`, `tests/`.
- [ ] Define the golden test set strategy (20–30 hand-labelled example conversations per classifier/extractor).

**Deliverables:**
- Problem framing doc (this file).
- Evidence schema + taxonomy skeleton.
- Golden-set labelling guide.
- Repository scaffold.

**Exit Criteria:**
- A new evaluator reading Phase 1 outputs can independently answer "what are we researching and how will we know what counts as evidence?"

---

### Phase 2 — Data Collection Layer

**Goal:** Build the collection pipeline and produce a real, raw corpus of publicly available conversations.

**Tech Stack:**
- HTTP: `httpx`/`requests` with retry + rate-limit handling.
- Reddit: `PRAW` (official API).
- Google Play reviews: `google-play-scraper` (Python).
- App Store reviews: `app-store-scraper` (Python).
- YouTube comments (optional): `google-api-python-client`.
- Storage: append-only JSONL per source + SQLite mirror (`sqlite3`/`SQLAlchemy`).

**Tasks:**
- [ ] Build **source adapters** for each selected source:
  - App Store reviews (iOS) — via public feeds/API.
  - Google Play Store reviews — via public endpoint/scraper.
  - Reddit — via official API (PRAW), subreddits: e.g. r/IndianFashion, r/fashionadvice, r/OnlineShoppingIndia, r/myntra (where they exist), plus search for AJIO / Nykaa Fashion / online fashion shopping discussions.
  - Optional: YouTube comments (Data API), fashion forums, public blogs/community threads.
- [ ] Implement **collection orchestration** (scheduled/manual run, rate-limit aware).
- [ ] Implement **dedup at collection time** (external_id, url, hash of text).
- [ ] Persist raw corpus as versioned JSONL + DB records with full metadata (source, url, author, timestamp, engagement).
- [ ] Store source/URL ethics + attribution metadata (for compliance & traceability).
- [ ] Log collection statistics (per-source counts, date ranges).

**Inputs:** source list (from Phase 1), target volume budget.
**Outputs:** `raw_corpus` dataset.

**Deliverables:** collection scripts, source config, raw dataset with metadata, collection run report.

**Exit Criteria:** ≥ N genuine conversations collected across ≥ 2 primary sources, with no broken records, all traceable to a source URL.

---

### Phase 3 — Cleaning, Deduplication & Relevance Filtering

**Goal:** Produce a high-quality **relevant corpus** — only conversations that actually talk about wishlist behaviour, purchase intention/hesitation, product comparison, fashion decision-making, uncertainty, or shopping behaviour.

**Tech Stack:**
- Data frames: `pandas`; text normalization with stdlib (`re`, `unicodedata`).
- Near-dup detection: SimHash/min-hash or embeddings (`sentence-transformers`) + cosine threshold.
- Relevance classifier: keyword rules + LLM classification via Claude/GPT API returning structured JSON (`pydantic` schema validation).
- Language detection: `langdetect`.

**Tasks:**
- [ ] Implement cleaning transforms:
  - Normalize text (whitespace, unicode, emoji/URL removal options, language detection).
  - Remove duplicates (exact + near-duplicate via embedding similarity / min-hash).
  - Remove spam, bot-generated content, ads, unrelated promotions.
  - Filter out non-English/irrelevant language if out of scope (configurable).
- [ ] Implement **Relevance Classifier**:
  - Hybrid: keyword rules + LLM classification with structured output and reasoning.
  - Labels: `relevant / not_relevant`, plus `relevance_category` (wishlist behaviour, purchase intention, purchase hesitation, product comparison, fashion decision-making, uncertainty, shopping behaviour, other).
- [ ] Human review pass on a sample to measure classifier accuracy vs golden set (target ≥ 85% agreement).
- [ ] Log filtering funnel stats (collected → cleaned → relevant), preserving counts for later frequency reporting.

**Inputs:** raw_corpus (Phase 2).
**Outputs:** `clean_corpus`, `relevant_corpus` (+ filtering funnel stats).

**Deliverables:** cleaning + classifier scripts, filtering report, classifier accuracy report.

**Exit Criteria:** relevant corpus is clean, deduplicated, and each record tagged with relevance category; classifier accuracy documented on the golden set.

---

### Phase 4 — Behaviour, Barrier & Unmet-Need Extraction

**Goal:** Convert relevant conversations into structured, evidence-linked insight records — the heart of the Discovery Engine.

**Tech Stack:**
- LLM extraction: Claude/GPT API, one structured JSON payload per conversation, validated with `pydantic`; prompt templates kept in `config/prompts/`.
- Batching: `asyncio` + concurrency with token-budget chunking and exponential-backoff retry.
- Embeddings: OpenAI `text-embedding-3-small` (or `sentence-transformers`) for later clustering.
- Vector store: ChromaDB or SQLite-vec; evidence packets in SQLite + JSONL.

**Tasks:**
- [ ] Build **Behaviour Extractor** (LLM + schema validation):
  - Extract what the user was *trying to do* (multi-label, from behaviour taxonomy).
  - Example behaviours: shortlist products, compare products, wait before buying, check fit, check quality, seek social validation, find something for an occasion, remember product for later, price-check, gift shopping, self-shopping.
  - Also extract: user role (shopping for self / others), stage in the funnel (saved → evaluating → hesitating → abandoned).
- [ ] Build **Barrier Extractor** (multi-label):
  - Map to hypothesis library (fit, size, quality, looks-in-reality, styling, occasion, reviews, authenticity, price, wait/spend, comparison, social validation, availability, delivery, returns, urgency, forgetting, bookmarking).
  - Capture explicit "why" wording verbatim.
- [ ] Build **Unmet-Need Inference**:
  - Ask "What information, confidence, functionality, or experience was missing?"
  - Output must remain distinct from raw quote (preserve the 3-level distinction).
- [ ] Build the **Evidence Packet** generator per conversation:
  - `quote` (verbatim snippet) + `behaviours` + `barriers` + `unmet_needs` + `segment hints` + `source` + `confidence`.
- [ ] Validate extractor outputs on golden set; iterate prompts/schema until acceptable (target ≥ 80% agreement on labelled items).
- [ ] Optionally store per-conversation embeddings for later clustering.

**Inputs:** relevant_corpus (Phase 3), taxonomies (Phase 1).
**Outputs:** `extracted_insights` dataset (behaviour records, barrier records, unmet-need records).

**Deliverables:** extractor scripts + prompt configs, extraction accuracy report, sample of 20 fully worked evidence packets.

**Exit Criteria:** a human can read any evidence packet and see exactly (a) the raw quote, (b) what we inferred, (c) what we conclude — with all three clearly separated.

---

### Phase 5 — Segmentation, Theme Clustering & Quantification

**Goal:** Discover patterns *across* conversations: which behaviours co-occur, which user segments exist, and how frequent each pattern is.

**Tech Stack:**
- Clustering: `scikit-learn` (KMeans) + `hdbscan` for density-based segments; embeddings from Phase 4 as features.
- Quantification: `pandas` + `polars` aggregation, co-occurrence matrices, CSV export (spreadsheets/Sheets).
- Visualizations (working docs): `matplotlib`/`plotly`; results saved as static PNG/HTML in `docs/`.

**Tasks:**
- [ ] **Segment Classification:** derive segments from data using behaviour + context features (embedding clustering + rule heuristics). Candidate segments to *test against* data (not assume): first-time shoppers, frequent shoppers, high-frequency wishlist users, occasion-based shoppers, shopping-for-self, shopping-for-others, budget-conscious, fashion-conscious, multi-product comparers, repeated sizing-concern users.
- [ ] **Theme Clustering:** cluster evidence packets by behaviour+barrier vectors; extract cluster labels; ensure clusters map to opportunity themes.
- [ ] **Quantification:**
  - Number of relevant conversations per theme.
  - Number of users mentioning each barrier/behaviour.
  - % of relevant conversations.
  - Frequency by source.
  - Frequency by segment.
  - Recurring behaviour patterns (co-occurrence matrices: e.g., save-multiple + can't-decide).
- [ ] **Impact-Weighted Reporting:** clearly separate *frequency of mention* from *evidence of business impact* (e.g., a barrier that shows up in active decision-friction stories ranks differently from a passive complaint).
- [ ] Validate clusters/segments on golden set and via a quick human sanity check (are the labels coherent?).

**Inputs:** extracted_insights (Phase 4).
**Outputs:** segment assignments, theme clusters, quantification tables.

**Deliverables:** clustering scripts, segment/theme reports, quantification tables (CSV/Sheets), co-occurrence analysis.

**Exit Criteria:** every segment and theme is traceable to ≥ 3 concrete evidence packets; frequency tables exist per source and segment.

---

### Phase 6 — Opportunity Ranking, Evidence DB & Discovery Dashboard

**Goal:** Turn analysed data into a **PM decision tool**: ranked opportunities, a browsable evidence database, and a testable end-to-end workflow.

**Tech Stack:**
- Dashboard: **Streamlit** (runnable, evaluator-testable) with an evidence-browser UI.
- Evidence DB: SQLite (single portable file) + ChromaDB for semantic search over quotes.
- Scorer/reports: pure Python + `pandas`; Discovery Report exported as Markdown/HTML.
- Interview questions: LLM-generated from ranked opportunities, templated and stored per opportunity.

**Tasks:**
- [ ] Build **Opportunity Scorer**:
  - Weighted dimensions (see Section 7.1): frequency, severity, purchase impact, users affected, evidence strength, segment concentration, existing workaround, product leverage.
  - Produce a ranked list with a transparent score breakdown (not a black box).
- [ ] Build **Evidence Database**:
  - Browsable/searchable store linking each opportunity/theme/barrier → evidence packets → raw quotes → source URL.
  - Store confidence per insight.
- [ ] Build **Discovery Dashboard / Report** (Streamlit or static HTML):
  - Input box: research question (e.g., "Why do users wishlist dresses but don't purchase them?").
  - Outputs: top barriers, user segments, behaviour patterns, frequencies, supporting quotes/evidence, opportunity ranking, and the three-level distinctions.
- [ ] Build **Interview Question Generator**:
  - From each ranked opportunity, auto-draft 2–3 open-ended interview questions targeting that behaviour/segment (to feed the required 5–6 primary interviews).
- [ ] Write the **Discovery Report** summarizing: evidence database, behaviour taxonomy, barrier taxonomy, segments, ranked opportunities, evidence per opportunity, and draft interview questions.
- [ ] **End-to-end acceptance test:** run the full pipeline (Phase 2 → 6) on the actual data with a fresh research question and capture a run report.

**Inputs:** all Phase 4/5 outputs.
**Outputs:** ranked opportunities, evidence DB, dashboard, interview questions, final report.

**Deliverables:** scorer + dashboard + evidence DB + final Discovery Report + run report.

**Exit Criteria:** an evaluator can run the workflow, see analysed conversations, inspect evidence, compare opportunity areas, and read a clear ranked output with interview questions — fully traceable to raw data.

---

## 7. Cross-Cutting Concerns

### 7.1 Opportunity Scoring Dimensions (weighted)

| Dimension | Weight (example) | Meaning |
|-----------|------------------|---------|
| Frequency | 0.20 | Share of relevant conversations mentioning the theme |
| Severity | 0.15 | How far it blocks the funnel (e.g., post-evaluation drop-off vs passive forgetfulness) |
| Purchase impact | 0.20 | Estimated effect on Wishlist → Purchase 30-day conversion |
| Users affected | 0.10 | Size of segment concentration |
| Evidence strength | 0.15 | Quality/consistency of quotes, confidence of extraction |
| Segment concentration | 0.05 | Concentration in a targetable segment |
| Existing workaround | 0.10 | Are users solving it elsewhere (e.g., comparing on other apps)? |
| Product leverage | 0.05 | Feasibility of a product intervention |

> Weights are a starting point and must be justified in the report — the engine should show *why* opportunity A beats B.

### 7.2 Evidence & Confidence Tiers

- **High:** multiple independent users, consistent language, direct behavioural description.
- **Medium:** recurring theme but indirect language or single-source concentration.
- **Low:** anecdotal, ambiguous, or single mention.

### 7.3 The Three-Level Distinction (enforced everywhere)

| Level | Definition | Example |
|-------|-----------|---------|
| Said | Verbatim user quote | "I saved it because I liked it but wanted to see other options." |
| Inferred | Structured behaviour | User is comparing alternatives before purchasing. |
| Concluded | Barrier / opportunity hypothesis | Comparison may delay wishlist → purchase conversion. |

### 7.4 Ethics & Compliance

- Only publicly available data; respect platform ToS and Reddit/API rate limits.
- Never publish personal data beyond what is public; use handles/IDs, no PII enrichment.
- Attribute sources for traceability.
- If any platform terms restrict scraping, switch to supported APIs or documented manual exports.

---

## 8. Data & Evidence Model

### 8.1 Conversation (raw)

```
id, source, source_external_id, url, author, timestamp,
text, language, engagement_metrics (likes/comments/score),
collected_at, raw_hash, is_duplicate_of
```

### 8.2 Relevant Conversation

```
conversation_id, relevance_category, relevance_reason, classifier_version
```

### 8.3 Evidence Packet (extracted)

```
conversation_id, quote (verbatim), quote_char_start/end,
intent (purchase / bookmark / save-for-later / occasion / gift / unknown),
behaviours [multi-label],
barriers [multi-label],
unmet_needs [multi-label],
user_role (self / other / unknown),
funnel_stage,
segment_hints [multi-label],
confidence (per label),
extractor_version
```

### 8.4 Insight (analysed)

```
insight_id, theme, behaviour_pattern, barrier, segment,
evidence_packet_ids [],
source_frequency, percentage_of_relevant,
evidence_strength, confidence, notes
```

### 8.5 Opportunity

```
opportunity_id, title, behaviour, barrier, segment,
score, score_breakdown (per dimension),
supporting_evidence_ids [],
existing_workarounds, product_leverage_notes,
proposed_interview_questions []
```

---

## 9. Testing & Evaluation Strategy

- **Golden set:** 20–30 hand-labelled conversations per classifier/extractor, fixed before tuning.
- **Accuracy metrics:** precision/recall/agreement for relevance classifier and each extractor label.
- **E2E acceptance test:** fresh research question → full pipeline → inspect outputs (conversations, behaviours, barriers, segments, opportunities, evidence, interview questions).
- **Negative tests:** spam-only input, non-English input, empty corpus → pipeline must fail gracefully with a clear report.
- **Reproducibility:** every dataset versioned; runs recorded with config + model versions + timestamps.

---

## 10. Risk Register & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Insufficient relevant data in chosen sources | High | Source expansion list prepared (YouTube comments, forums, blogs); broad subreddit search list |
| Classifier/extractor accuracy too low | High | Golden-set-driven iteration; human review pass on sample; confidence labels surface ambiguity |
| Platform ToS / scraping limits | Medium | Prefer official APIs; fallback to manual/public exports; documented approach |
| LLM cost at scale | Medium | Batch + caching; sample-stratified extraction before full-run |
| Frequency ≠ impact confusion | Medium | Impact-weighted scoring + funnel-stage tagging baked into pipeline |
| Evaluator can't reproduce run | Medium | Versioned data, run config, one-command pipeline, run report |

---

## 11. Success Criteria

The Discovery Engine is successful if, after using it, we can confidently say:

> "I started with an unknown wishlist-to-purchase problem. I analyzed user conversations at scale, identified recurring behaviours and barriers, quantified the strongest patterns where possible, compared opportunity areas, and now know which problem I should validate with real users."

**It fails if the result is:** "I analyzed 10,000 reviews and found that users have positive and negative opinions."

That is sentiment analysis. The first statement is Product Discovery. This project is the first.

### Phase-end success checklist (final report must contain)

- [ ] **A. Evidence database** — actual conversations with source info.
- [ ] **B. Behaviour taxonomy** — behaviours discovered from data.
- [ ] **C. Barrier taxonomy** — reasons users postpone/avoid purchase.
- [ ] **D. User segments** — segments linked to different barriers.
- [ ] **E. Opportunity areas** — ranked by evidence + impact.
- [ ] **F. Evidence per opportunity** — traceable user quotes.
- [ ] **G. Interview research questions** — ready for the 5–6 user interviews.

---

## 12. Open Questions for Evaluator / Mentor

1. Are app-store review collections (via public feeds) preferred over scraped HTML? Any compliance constraints?
2. Which Reddit / community sources are acceptable given the platform context?
3. Is a local SQLite + ChromaDB stack acceptable, or is a specific AI stack (n8n, etc.) required by the assignment?
4. Target corpus volume expectation (e.g., "1,000+ relevant conversations") — is there a minimum bar?
5. Should the dashboard be a runnable app (Streamlit) or a static report for evaluation?

---

*Working draft — Phase 1 output. To be evolved as evidence is collected.*
