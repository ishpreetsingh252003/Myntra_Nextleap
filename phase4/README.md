# Phase 4 — Behaviour, Barrier & Unmet-Need Extraction

> Working Principle (keep at top of all working documents):
> Don't build the solution I think is right. Build the discovery system that helps me find the problem worth solving.
>
> Companions: [`ARCHITECTURE_6_PHASE_PLAN.md`](../../ARCHITECTURE_6_PHASE_PLAN.md) §4 Phase 4, [`EDGE_CASES.md`](../../EDGE_CASES.md) §4.

Converts each relevant conversation into a structured **Evidence Packet** — the
heart of the Discovery Engine. Every packet contains a verbatim quote with
character offsets, multi-label behaviour/barrier/unmet-need extraction,
user role, funnel stage, segment hints, confidence, and the **three-level
distinction** (said / inferred / concluded) that keeps evidence traceable.

## Components

| Module | What it does |
|--------|-------------|
| `src/behaviour.py` | multi-label behaviour extraction (BEH-01..BEH-12) |
| `src/barrier.py` | multi-label barrier extraction (PB-01..PB-18) |
| `src/unmet_needs.py` | unmet-need inference from barriers + text signals |
| `src/evidence.py` | evidence packet assembly + quote offset validation (EC-24/25) |
| `src/llm.py` | optional Claude/GPT extractor (offline fallback, EC-39/41) |
| `src/embeddings.py` | per-conversation TF-IDF vectors for Phase 5 clustering |
| `src/evaluator.py` | golden-set precision/recall/F1/agreement |
| `src/pipeline.py` | orchestrates extraction + embeddings + storage |
| `src/storage.py` | SQLite mirror + JSONL evidence packets |
| `src/report.py` | accuracy report + sample evidence packets |
| `src/cli.py` | CLI interface |

## Three-level distinction (never conflated)

- **Said:** verbatim quote from the source text
- **Inferred:** behaviours and barriers we reasonably infer from language
- **Concluded:** opportunity hypotheses needing corroboration across multiple packets

## Accuracy on the golden set

Golden set: `data/golden_set/evidence_golden.jsonl` (20 hand-labelled packets
with behaviours, barriers, unmet_needs, intent, user_role, funnel_stage,
segment_hints, and three_level distinction).

Deterministic rule baseline (`extraction-v1.0`, offline, no API key):

| Metric | Score |
|--------|-------|
| Behaviour F1 (avg) | 0.66 |
| Barrier F1 (avg) | 0.60 |
| Overall agreement | **0.629** |
| Three-level pass rate | **1.0** |
| Intent accuracy | 0.80 |

Architecture target: ≥ 80% with LLM as decision-maker. The rule baseline
achieves 62.9% — reasonable for an offline deterministic system; LLM
significantly improves multi-label accuracy on ambiguous texts.

Edge cases handled: EC-19 (multi-label never collapsed), EC-20 (NONE-STATED
when no barrier), EC-21 (implied barriers at "inferred" level), EC-22
(contradictions extracted with both labels), EC-23 (user_role detected),
EC-24 (quote offset validated), EC-25 (offsets re-derived from cleaned text),
EC-26 (funnel stage extracted explicitly).

## Run it

```bash
cd phase4/backend
python -m pip install -r requirements.txt

# 1. run extraction on the Phase 3 relevant corpus
python -m src.cli run

# 2. golden-set accuracy
python -m src.cli accuracy

# 3. sample evidence packets
python -m src.cli sample --n 5

# 4. report
python -m src.cli report
```

Optional LLM extractor — copy `.env.example` → `.env`, set `ANTHROPIC_API_KEY`
(or `OPENAI_API_KEY`), re-run. Reports then show `decision_source=llm`.

## Layout

```
phase4/
  backend/
    src/
      behaviour.py     # multi-label behaviour extraction (rule + LLM)
      barrier.py       # multi-label barrier extraction (rule + LLM)
      unmet_needs.py   # unmet-need inference
      evidence.py      # packet assembly + quote offset validation
      llm.py           # optional Claude/GPT provider
      embeddings.py    # TF-IDF + ChromaDB slot
      evaluator.py     # golden-set evaluation
      pipeline.py      # orchestrates extraction
      storage.py       # SQLite + JSONL
      report.py        # accuracy + sample reports
      cli.py
      config.py
    config/extraction.yaml   # taxonomies, signals, LLM settings
    tests/test_phase4.py     # 19 tests
  data/
    golden_set/evidence_golden.jsonl  # 20 hand-labelled packets
    output/                            # regenerated (ignored except *.md)
```

## Exit criteria (from architecture)

- [x] evidence packets with quote + behaviours + barriers + unmet_needs + three_level
- [x] multi-label extraction (never collapsed, EC-19)
- [x] NONE-STATED when no barrier (EC-20)
- [x] three-level distinction always present (said / inferred / concluded)
- [x] quote offset validated or re-derived (EC-24/25)
- [x] accuracy documented on the golden set
- [x] per-conversation embeddings for Phase 5 clustering