# Phase 5 — Segmentation, Theme Clustering & Quantification

> Working Principle: Don't build the solution I think is right. Build the discovery system that helps me find the problem worth solving.
>
> Companions: [`ARCHITECTURE_6_PHASE_PLAN.md`](../../ARCHITECTURE_6_PHASE_PLAN.md) §4 Phase 5, [`EDGE_CASES.md`](../../EDGE_CASES.md) §5.

Discovers patterns *across* conversations: user segments, thematic clusters, behaviour co-occurrences, and frequency tables — clearly separating frequency of mention from evidence of business impact.

## Components

| Module | What it does |
|--------|-------------|
| `src/segmentation.py` | assigns segments (SEG-01..SEG-10) from behaviours + text signals |
| `src/clustering.py` | theme clustering via TF-IDF + KMeans/Agglomerative |
| `src/quantification.py` | frequency tables, co-occurrence matrices, per-source/per-segment breakdown |
| `src/evaluator.py` | validates clusters/segments >= 3 packets (architecture exit criteria) |
| `src/pipeline.py` | orchestrates segmentation -> clustering -> quantification |
| `src/storage.py` | SQLite mirror + CSV quantification tables |
| `src/report.py` | summary report (markdown) |
| `src/cli.py` | CLI interface |

## Run it

```bash
cd phase5/backend
python -m pip install -r requirements.txt

# run on Phase 4 evidence packets
python -m src.cli run

# validate exit criteria
python -m src.cli validate

# summary report
python -m src.cli report
```

## Exit criteria

- [x] every segment and theme traceable to evidence packets
- [x] frequency tables exist per source and segment
- [x] co-occurrence matrices for behaviour x barrier
- [x] validator flags clusters with < 3 packets (architecture §9)