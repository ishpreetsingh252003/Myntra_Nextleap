# Golden Set Labelling Guide (Phase 1)

## Purpose

A **golden set** is a fixed, hand-labelled collection of conversations used to measure classifier/extractor accuracy before tuning (see `ARCHITECTURE_6_PHASE_PLAN.md` Section 7). It must be created and frozen **before** tuning models, and expanded per phase.

## Rules

1. **Labelled by humans, from real (or clearly synthetic) conversations** — never from model output.
2. **Frozen:** once a golden set for a stage is agreed, it is not edited during tuning. Changes require a version bump and a recorded reason.
3. **Conflicts:** if two labelers disagree on an item, resolve it by discussion; record the resolution. Measure inter-labeler agreement on a double-labelled subset.
4. **Coverage:** include easy and hard examples — including edge cases from `EDGE_CASES.md` (e.g., the "I wish this were better quality" verb trap, multi-barrier posts, implied barriers).
5. **Traceability:** every label must be justified by the same three-level distinction used in extraction.

## Target sizes (per classifier / extractor)

| Stage | Target items | Where |
|-------|--------------|-------|
| Relevance classification (Phase 3) | 20–30 conversations | `data/golden_set/golden_relevance_*.json` |
| Behaviour/barrier extraction (Phase 4) | 20–30 conversations (≥ 40 evidence packets) | `data/golden_set/golden_evidence_sample.json` (seed) |

## Evidence packet labelling — what to fill

For each conversation, produce an evidence packet following `schemas/evidence.schema.json`:

- **said** — verbatim quote from the source text.
- **inferred** — the structured behaviour we reasonably infer from that quote.
- **concluded** — the barrier / opportunity hypothesis, stated as a hypothesis.

## Judgement levels

- `observed` — directly stated by the user.
- `inferred` — reasonably inferred; must point back to the quote.
- `concluded` — a hypothesis that needs corroboration across multiple packets; never written as fact.

## Confidence levels

- `high` — quote directly supports the label; multiple independent users expected to agree.
- `medium` — language supports it but is indirect.
- `low` — weak, ambiguous, or single-source support.

## Validation

After labelling, run:

```
python scripts/validate_evidence.py --sample
```

and (once Phase 3/4 goldens exist) the pytest suite in `tests/`.