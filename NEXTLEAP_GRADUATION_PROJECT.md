# NextLeap Graduation Project — AI-Powered Fashion Wishlist Discovery Engine

> **Working Principle (keep at top of all working documents):**
> Don't build the solution I think is right. Build the discovery system that helps me find the problem worth solving.

---

## Project Index

This project is documented in **two separate files**:

### 1. Problem Statement — [`problemstatementbrief.md`](problemstatementbrief.md)

Business context, the core research question ("Why does a user who has explicitly wishlisted a fashion product not purchase it within the next 30 days?"), wishlist-intent and purchase-barrier hypotheses, sources to analyze, what the engine should **not** do, evidence requirements, and the success criterion.

### 2. Architecture Plan — [`ARCHITECTURE_6_PHASE_PLAN.md`](ARCHITECTURE_6_PHASE_PLAN.md)

Solution overview, high-level pipeline, tech stack, and the **6-phase build plan** (each phase: goal, tech, tasks, inputs/outputs, deliverables, exit criteria):

| Phase | Name | Focus |
|-------|------|-------|
| 1 | Discovery Foundation & Problem Framing | Research instrument, taxonomies, evidence schema |
| 2 | Data Collection Layer | Public conversation scrapers + raw corpus |
| 3 | Cleaning & Relevance Filtering | Dedup, spam removal, relevance classifier |
| 4 | Behaviour, Barrier & Unmet-Need Extraction | AI extraction of evidence packets |
| 5 | Segmentation & Quantification | Theme clustering, segments, frequency tables |
| 6 | Opportunity Ranking & Dashboard | Scorer, evidence DB, Streamlit dashboard, interview questions |

### 3. Edge Cases — [`EDGE_CASES.md`](EDGE_CASES.md)

Corner cases for every pipeline stage (collection → extraction → scoring → dashboard), plus LLM/reproducibility and research-framing edge cases, each with impact and handling strategy.

---

Then cross-cutting concerns (opportunity scoring, confidence tiers, ethics), data model, testing strategy, risks, and success criteria are inside the architecture plan.

### 4. Code Structure — phase folders (`phase1/` … `phase6/`)

Each phase builds in its own folder with its own `README.md`. **Phase 1 is implemented** — see [`phase1/README.md`](phase1/README.md): taxonomies, sources plan, evidence schema, validation script, golden-set seed, and passing tests. **Phase 2 is implemented** — see [`phase2/backend/README.md`](phase2/backend/README.md): collection adapters, dedup, JSONL+SQLite raw corpus, run report, and offline fixture mode. **Phase 3 is implemented** — see [`phase3/README.md`](phase3/README.md): cleaning + dedup + relevance classifier (rule baseline, optional LLM decision-maker), golden-set accuracy report (95.8% agreement), and funnel statistics. **Phase 4 is implemented** — see [`phase4/README.md`](phase4/README.md): behaviour/barrier/unmet-need extraction, evidence packets with three-level distinction, TF-IDF embeddings for clustering, golden-set accuracy (62.9% rules baseline, LLM target ≥80%), and 20 hand-labelled golden packets. **Phase 5 is implemented** — see [`phase5/README.md`](phase5/README.md): segment assignment, theme clustering (KMeans), quantification tables (behaviour/barrier frequencies, co-occurrence matrices, per-source/per-segment breakdown), and cluster validation. **Phase 6 is implemented** — see [`phase6/README.md`](phase6/README.md): weighted opportunity scoring (8 dimensions), evidence DB linking opportunities → packets → quotes → source URLs, interview question generator, and Discovery Report.