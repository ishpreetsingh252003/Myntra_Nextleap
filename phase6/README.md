# Phase 6 — Opportunity Ranking, Evidence DB & Discovery Report

> Working Principle: Don't build the solution I think is right. Build the discovery system that helps me find the problem worth solving.
>
> Companions: [`ARCHITECTURE_6_PHASE_PLAN.md`](../../ARCHITECTURE_6_PHASE_PLAN.md) §4 Phase 6.

Turns analysed data into a PM decision tool: ranked opportunities, browsable evidence database, interview questions, and the final Discovery Report.

## Components

| Module | What it does |
|--------|-------------|
| `src/scorer.py` | weighted opportunity scoring (8 dimensions, architecture §5.1) |
| `src/interview.py` | 2-3 open-ended interview questions per ranked opportunity |
| `src/evidence_db.py` | SQLite evidence DB linking opportunities → packets → quotes → source URLs |
| `src/report.py` | Discovery Report (markdown) with ranked opportunities + methodology |
| `src/pipeline.py` | orchestrates scoring → interview questions → evidence DB → report |
| `src/storage.py` | SQLite opportunity store + run bookkeeping |
| `src/cli.py` | CLI interface |

## Scoring dimensions (architecture §5.1)

| Dimension | Weight | Meaning |
|-----------|--------|---------|
| Frequency | 0.20 | Share of relevant conversations mentioning the theme |
| Severity | 0.15 | How far it blocks the funnel |
| Purchase impact | 0.20 | Effect on Wishlist → Purchase conversion |
| Users affected | 0.10 | Size of segment concentration |
| Evidence strength | 0.15 | Quality/consistency of quotes |
| Segment concentration | 0.05 | Concentration in a targetable segment |
| Existing workaround | 0.10 | Are users solving it elsewhere? |
| Product leverage | 0.05 | Feasibility of a product intervention |

## Run it

```bash
cd phase6/backend
python -m pip install -r requirements.txt

# run on Phase 4 packets + Phase 5 quantification
python -m src.cli run

# view ranked opportunities
python -m src.cli opportunities

# discovery report
# -> data/output/discovery_report.md
```

## Exit criteria

- [x] ranked opportunities with transparent score breakdown
- [x] evidence DB linking opportunities → packets → quotes → source URLs
- [x] interview questions per opportunity
- [x] Discovery Report with methodology, findings, and ranked output