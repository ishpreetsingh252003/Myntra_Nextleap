# Myntra NextLeap — AI-Powered Fashion Wishlist Discovery Engine

> Don't build the solution I think is right. Build the discovery system that helps me find the problem worth solving.

This repository contains the NextLeap Graduation Project: an AI-powered **Discovery Engine** that analyzes publicly available user conversations about online fashion shopping to uncover why users wishlist fashion products but fail to purchase them within 30 days.

## Documents

- **`NEXTLEAP_GRADUATION_PROJECT.md`** — project index.
- **`problemstatementbrief.md`** — problem statement, research question, hypotheses, evidence requirements.
- **`ARCHITECTURE_6_PHASE_PLAN.md`** — architecture plan and the 6-phase roadmap.
- **`EDGE_CASES.md`** — pipeline edge cases (collection → dashboard) with handling strategies.

## Planned Phases

Each phase lives in its own folder. All 6 phases are implemented.

1. Discovery Foundation & Problem Framing → [phase1/README.md](phase1/README.md)
2. Data Collection Layer → [phase2/backend/README.md](phase2/backend/README.md)
3. Cleaning & Relevance Filtering → [phase3/README.md](phase3/README.md)
4. Behaviour, Barrier & Unmet-Need Extraction → [phase4/README.md](phase4/README.md)
5. Segmentation, Theme Clustering & Quantification → [phase5/README.md](phase5/README.md)
6. Opportunity Ranking, Evidence DB & Discovery Report → [phase6/README.md](phase6/README.md)

## Run the whole thing (deployable backend)

- **[FastAPI backend](app/README.md)** — one API that scrapes live reviews, runs all 6 phases with free Groq/Gemini LLMs, and returns ranked opportunities backed by evidence quotes. Deploys to Render (`render.yaml`).
- **[One-command orchestrator](scripts/orchestrate.py)** — runs the full pipeline from terminal:
  ```bash
  python scripts/orchestrate.py --fixtures
  python scripts/orchestrate.py --sources google_play app_store --from-date 2026-01-01 --to-date 2026-08-19
  ```
- Frontend lives separately (Vercel) and calls the backend's `/api/*` endpoints.
