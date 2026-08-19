# Phase 1 — Discovery Foundation & Problem Framing

> Companion: [`problemstatementbrief.md`](../problemstatementbrief.md) · [`ARCHITECTURE_6_PHASE_PLAN.md`](../ARCHITECTURE_6_PHASE_PLAN.md) · [`EDGE_CASES.md`](../EDGE_CASES.md)

## Goal

Turn the business question into a **testable research instrument** and define the **evidence model** before touching data.

**Tech stack:** Python 3.11+, `pytest`, `.env` for API keys, Claude/GPT API (used in later phases).

## Deliverables

| Deliverable | Location | Status |
|-------------|----------|--------|
| Problem statement brief | `problemstatementbrief.md` (repo root) | Done |
| Client-side research setup (`.env.example`) | `.env.example` | Done |
| Behaviour taxonomy skeleton | [`config/taxonomies/behaviours.yaml`](config/taxonomies/behaviours.yaml) | Done |
| Barrier hypothesis library | [`config/taxonomies/barriers.yaml`](config/taxonomies/barriers.yaml) | Done |
| Candidate segmentation dimensions | [`config/taxonomies/segments.yaml`](config/taxonomies/segments.yaml) | Done |
| Source selection + access plan | [`config/sources.yaml`](config/sources.yaml) | Done (proposed statuses) |
| Evidence packet schema | [`schemas/evidence.schema.json`](schemas/evidence.schema.json) | Done |
| Evidence validation script | [`scripts/validate_evidence.py`](scripts/validate_evidence.py) | Done |
| Golden-set labelling guide + seed sample | [`data/golden_set/`](data/golden_set/) | Done (seed; expand Phase 3/4 to 20–30) |
| Phase 1 tests | [`tests/test_phase1_foundations.py`](tests/test_phase1_foundations.py) | Done |

## Three-level distinction (project rule)

Every insight keeps these separate (enforced by the evidence schema):

1. **Said** — verbatim quote.
2. **Inferred** — structured behaviour we reasonably infer.
3. **Concluded** — barrier/opportunity hypothesis requiring corroboration.

## Golden set strategy

- Size targets: 20–30 conversations for relevance (Phase 3) and extraction (Phase 4).
- Frozen + versioned before tuning; conflicts resolved with recorded inter-labeler agreement.
- Seed sample: `data/golden_set/golden_evidence_sample.json` (3 packets, validates against schema).

## How to run

```bash
cd phase1
python -m pip install -r requirements.txt
python scripts/validate_evidence.py --sample          # validates golden sample + taxonomy refs
python -m pytest tests/ -q                            # runs schema + taxonomy tests
```

## Exit criteria (from architecture plan)

- [ ] An evaluator reading Phase 1 outputs can independently answer **"what are we researching and how will we know what counts as evidence?"**
  - Research question + hypotheses → `problemstatementbrief.md`
  - Evidence model → `schemas/evidence.schema.json` + `data/golden_set/README.md`

## Edge cases covered in this phase

- EC-41 (missing API key) → `.env.example` + fail-fast validation built in later phases.
- EC-45 (golden set mislabeled) → labelling guide mandates double-labelling + agreement measurement.
- EC-48 / EC-49 / EC-50 (research-framing traps) → reflected in `sources.yaml` notes and golden-guide coverage rule.

## Next phase (Phase 2 — Data Collection Layer)

Will confirm source statuses, build source adapters (PRAW, google-play-scraper, app-store-scraper), orchestration, and the raw corpus in `phase2/backend`.