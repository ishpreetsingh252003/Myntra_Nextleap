# Edge Cases — AI-Powered Fashion Wishlist Discovery Engine

> Companion to [problemstatementbrief.md](problemstatementbrief.md) and [ARCHITECTURE_6_PHASE_PLAN.md](ARCHITECTURE_6_PHASE_PLAN.md).
> This register documents corner cases that can break each pipeline stage, with impact and handling strategy. It is a living document — add cases as they surface during Phase 2–6.

---

## 1. Collection Stage (Phase 2)

| ID | Edge Case | Impact | Handling |
|----|-----------|--------|----------|
| EC-01 | Source API returns empty / zero results | Pipeline stalls with no corpus | Return a structured "empty collection" report; allow manual CSV upload fallback for the source |
| EC-02 | API rate limits / 429s (Reddit, stores) | Partial collection, gaps | Exponential backoff + retry; resume from last cursor/external_id; log skipped records |
| EC-03 | Scraper breaks due to source page/API change | Adapter fails | Each adapter isolated; keep sample fixtures (`test_*.json`) to detect schema drift in tests |
| EC-04 | Non-English / Hinglish user text | Missed insights if filtered blindly | Keep language tag; do not silently drop — flag for bilingual extraction or translate only when needed |
| EC-05 | Duplicate reviews across sources (same text on App Store + Play Store) | Inflated frequency counts | Cross-source dedup by canonical text hash during cleaning |
| EC-06 | Bot / spam / AI-generated reviews with shopping words | Noise pollutes relevance | Spam heuristics + LLM bot-likeness label; route to a quarantine set, never delete silently |
| EC-07 | Hunters-only reviews (no text, only stars) | Zero-value records | Retain metadata but exclude from extraction; count separately in collection stats |
| EC-08 | Very long threads exceed LLM token limits | Extraction fails on big Reddit threads | Chunking strategy: summarize parent thread + extract per top-level comment; record truncated flag |
| EC-09 | Reviews referencing an unrelated product ("shoe review" inside a dress thread) | Off-topic conversations enter corpus | Relevance classifier handles; keep source context so reviewers can override |

---

## 2. Cleaning & Deduplication (Phase 3)

| ID | Edge Case | Impact | Handling |
|----|-----------|--------|----------|
| EC-10 | Exact duplicates differing only in whitespace/case/emoji | Double counting | Normalize before hashing (casefold, strip, collapse whitespace) |
| EC-11 | Near-duplicates (same user repeating a phrase across many products) | One behaviour counted many times | Embedding similarity threshold → keep representative, mark `is_duplicate_of` |
| EC-12 | Same user posting many threads/comments on the theme | Segment/frequency inflation | Track `author` + per-author caps; quantify at user level in addition to conversation level |
| EC-13 | Promotional noise — "great sale!", "just launched" with no behaviour | False relevance | Promotion/ad keyword rules pre-filter before LLM classification |
| EC-14 | PII in raw text (emails, order IDs, phone numbers, full names) | Compliance risk | Regex-mask PII; never enrich; never log raw author details |

---

## 3. Relevance Classification (Phase 3)

| ID | Edge Case | Impact | Handling |
|----|-----------|--------|----------|
| EC-15 | "I wish the dress was better quality" — `wish` verb, NOT wishlist feature | False positive | Classifier must distinguish wishlist/behaviour intent from the verb "wish"; confirm with golden set |
| EC-16 | Sarcasm / irony ("love waiting forever for my order") | Mislabeled barrier | LLM reasoning label + confidence; humans review the low-confidence bucket |
| EC-17 | Ambiguous references ("it", "this thing", "yaar") lacking context | Wrong category | Pass thread context to classifier; low-confidence flag for manual review |
| EC-18 | Genuine wishlist conversation with zero shopping keywords | False negative | Keyword rules are a pre-filter only; LLM is the decision-maker, keywords never the final gate |

---

## 4. Behaviour & Barrier Extraction (Phase 4)

| ID | Edge Case | Impact | Handling |
|----|-----------|--------|----------|
| EC-19 | Multi-barrier conversations (size + price + no reviews) | Must not collapse to one label | Multi-label extraction; each barrier gets its own label + confidence |
| EC-20 | High purchase intent but NO barrier stated | Empty barrier field | Represent as `intent=purchase, barrier=none-stated`; do NOT invent a barrier |
| EC-21 | Implied barrier (user says "kept looking for something else") | Over-inference risk | Keep it at "inferred" level; store verbatim quote; only "concluded" after multiple corroborating packets |
| EC-22 | Contradictory statements in one post (loves it but "won't buy") | Confusing extraction | Extract both with diverging confidence; flag for review rather than averaging |
| EC-23 | User recounts someone else's shopping, not their own | Wrong attribution to user | Extract `user_role`/`referential` flag; exclude or tag "observed behaviour" when inferring segments |
| EC-24 | LLM hallucinates a quote that isn't in the text | Fabricated evidence — fatal for credibility | Every quote validated against source text via char-offset match; mismatch → discard label + flag |
| EC-25 | Quote char offsets drift after cleaning/encoding | Evidence link breaks | Re-derive offsets from the cleaned canonical string at extraction time; store string + offsets together |
| EC-26 | Same product/size topic in past vs future tense ("I might buy" vs "I bought") | Funnel-stage mislabel | Extract tense/`funnel_stage` explicitly (saved → evaluating → hesitant → abandoned → purchased) |

---

## 5. Segmentation & Clustering (Phase 5)

| ID | Edge Case | Impact | Handling |
|----|-----------|--------|----------|
| EC-27 | Segments with only 1–2 evidence packets | False "segment" claim | Require minimum n (e.g., ≥ 3 packets) before naming a segment; merge small clusters into "other" |
| EC-28 | One user fits several segments (comparer + occasion shopper) | Overlap confusion | Allow multi-segment membership; report per-segment counts at packet/user level |
| EC-29 | Cluster mixes two distinct themes (fit + quality) | Blurry opportunity labels | Two-level check: vector distance + LLM cluster label + human sanity sample |
| EC-30 | Embedding domain ambiguity (fashion vs generic shopping) | Clusters drift off-topic | Cluster only on evidence packets already tagged `relevant` + use behaviour/barrier features too |

---

## 6. Quantification & Scoring (Phase 6)

| ID | Edge Case | Impact | Handling |
|----|-----------|--------|----------|
| EC-31 | One source dominates (e.g., 80% of corpus from Reddit) | Frequency numbers skewed | Always report frequency **by source**; cite source bias in the report |
| EC-32 | Thread counted once vs every comment counted | Inflated or deflated counts | Define count unit explicitly (top-level thread vs comment) and report both where ambiguous |
| EC-33 | Tiny sample (n=15 relevant conversations) | Percentages look dramatic | Suppress percentages below a minimum-n threshold; show raw counts + confidence tier instead |
| EC-34 | Very frequent barrier ≠ impactful barrier (forgetting) | Misleading ranking | Keep frequency separate from severity/purchase-impact weights; surface both scores side by side |
| EC-35 | Score ties between two opportunities | Ambiguous ranking | Tie-break on evidence strength then purchase impact; show score breakdown for transparency |
| EC-36 | Weights feel arbitrary | Arbitrary ranking | Justify weights in report; run sensitivity check (flip weights, confirm top-3 is stable) |

---

## 7. Dashboard & Report (Phase 6)

| ID | Edge Case | Impact | Handling |
|----|-----------|--------|----------|
| EC-37 | Empty research question submitted | Generic output | Prompt for the question; default to the core research question |
| EC-38 | Research question with no matching evidence | No results shown | Show nearest themes with low-match notice + guidance to broaden the question |
| EC-39 | Dashboard run with no API keys / offline | Breakage at eval time | Graceful "cached results" mode + clear setup message; never a raw stack trace |
| EC-40 | Corrupt/empty evidence DB on load | Dashboard blank | Startup validation with user-friendly error; auto-rebuild from JSONL fallback |

---

## 8. Cross-Cutting LLM & Reproducibility

| ID | Edge Case | Impact | Handling |
|----|-----------|--------|----------|
| EC-41 | API key missing / expired / quota exhausted | Entire pipeline stops | Fail-fast validation with clear error; env-driven keys; quota-aware batching |
| EC-42 | Model version drift between runs | Non-reproducible results | Pin model + prompt versions; record them in every run report |
| EC-43 | Non-deterministic LLM output on re-run | Different labels each run | Fixed temperature/seed where supported; store per-run artifacts; re-run only when prompts change |
| EC-44 | Retry storms on repeated failures | API abuse / cost | Cap retries (e.g., 3), exponential backoff, circuit-break after N failures with report |
| EC-45 | Golden set itself mislabeled (disagreement between human labelers) | Accuracy numbers look fake | Double-label a subset; measure inter-labeler agreement; resolve conflicts before tuning |

---

## 9. Research-Framing Edge Cases (must NOT be treated as findings)

| ID | Edge Case | Handling |
|----|-----------|----------|
| EC-46 | Users who purchased without wishlisting | Out of scope — not evidence for this project; exclude |
| EC-47 | Same-day wishlist → purchase (instantly bought) | Not the drop-off set; exclude from barrier analysis (they succeeded) |
| EC-48 | Users confuse wishlist with cart ("add to cart works but wishlist doesn't") | Could indicate a UX gap, not intent — label as product-functionality category, keep separate from behavioural barriers |
| EC-49 | Review is about returns/refunds but happens to say "I won't wishlist again" | Different journey; tag as post-purchase, separate bucket, do not mix into pre-purchase barriers |
| EC-50 | A "wishlist" mention is actually a song list / gift registry / other product category | Relevance classifier must gate on fashion + e-commerce shopping context |

---

## 10. How to Use This Document

- Treat it as a **checklist during each phase's build** — before calling a stage "done", confirm the relevant EC rows are handled.
- Any edge case discovered in real data that is not listed here → **add a row, implement handling, and include it in the run report**.
- Edge cases that change what counts as evidence (Section 9) must be reflected in the **taxonomies** and **evidence schema** before quantification happens.