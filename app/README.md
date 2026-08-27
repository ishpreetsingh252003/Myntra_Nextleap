# Discovery Engine — FastAPI Backend (Render)

The runnable, deployable API that ties all 6 phases together. One call scrapes
live reviews, runs the whole pipeline, and returns ranked opportunities backed
by evidence quotes.

## Run locally

```bash
cd <repo root>
pip install -r app/requirements.txt

# Option A: one-command whole pipeline (CLI)
python scripts/orchestrate.py --fixtures                          # offline demo
python scripts/orchestrate.py --sources google_play app_store --from-date 2026-01-01 --to-date 2026-08-19

# Option B: the API server
uvicorn app.main:app --reload --port 8000
```

## API

| Method | Path | Body | Purpose |
|--------|------|------|---------|
| GET  | `/api/health` | — | Render health check |
| POST | `/api/scrape` | `{sources, from_date, to_date}` | live scraping only |
| POST | `/api/analyze` | `{}` | run clean→extract→segment→score on scraped corpus |
| POST | `/api/run` | `{sources, from_date, to_date}` | scrape + analyze in one call |
| GET  | `/api/results` | — | evidence packets + opportunities + discovery report |
| GET  | `/api/opportunities` | — | ranked opportunities (score breakdown + interview questions) |

Example:
```bash
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"sources":["google_play","app_store"],"from_date":"2026-01-01","to_date":"2026-08-19"}'
```

## Environment (set in Render dashboard)

Free LLM keys (auto-detected, priority order):
- `GROQ_API_KEY` → Groq (fast, free)
- `GOOGLE_API_KEY` → Gemini (free tier)

Source credentials (for live scraping in `phase2/backend/.env`, copied by Render):
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` — Reddit live
- `YOUTUBE_API_KEY` — YouTube comments

Without any key, the pipeline still runs fully offline using the deterministic
rule baselines (great for a demo/eval).

## Deploy to Render

The repo includes:
- `render.yaml` — blueprint (free plan, health check, env vars)
- `Procfile` — `uvicorn app.main:app`

Either push to Render (auto-detect `render.yaml`) or create a new Web Service:
- Build: `pip install -r app/requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Root dir: repo root (so `app/`, `phase2/`…`phase6/` are all present)

> Render free instances sleep after inactivity; the first `/api/run` after sleep
> will be slower (cold start + full scrape+analyze) — show a loading state in the frontend.

## Frontend (Vercel)

Point your frontend at this backend's URL and call the `/api/*` endpoints. The
natural UX (matching your Gaana reference, but going further):

1. Source multi-select + date range → `POST /api/run`
2. While running → polling loading screen
3. Results → top barriers/segments, evidence quotes (with source URL),
   ranked opportunities, interview questions

## Directory

```
app/
  main.py            # FastAPI routes
  requirements.txt   # backend deps
  data/              # shared corpus (gitignored except reports/.gitkeep)
scripts/
  orchestrate.py     # one-command CLI running all 6 phases
render.yaml          # Render blueprint
Procfile             # Render start command
```
