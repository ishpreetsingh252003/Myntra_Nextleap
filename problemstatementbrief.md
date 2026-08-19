# Problem Statement Brief — AI-Powered Fashion Wishlist Discovery Engine

> **Working Principle (keep at top of all working documents):**
> Don't build the solution I think is right. Build the discovery system that helps me find the problem worth solving.

---

## 1. Context

I am a Product Manager on the **Growth Team** at Myntra (fashion e-commerce platform).

**Business goal:** Increase the percentage of users who purchase at least one product from their wishlist within 30 days of adding it.

**Why this matters:** A wishlist is a strong signal of explicit user interest. Yet many users save products without ever purchasing them. The company wants to understand:

> Why do users wishlist fashion products but fail to purchase them later?

**The underlying user problem is intentionally not provided.** The first responsibility as a PM is therefore **discovery**, not solution-building.

**North-star metric:** Wishlist → Purchase Conversion Rate (within 30 days).

---

## 2. Objective

Build an **AI-powered Discovery Engine** that analyzes large volumes of publicly available user conversations about online fashion shopping, and helps uncover the real reasons behind wishlist-to-purchase drop-off.

**The goal is NOT sentiment analysis or review summarization.** It is to discover:

- What users are trying to accomplish when they wishlist products,
- What prevents them from purchasing,
- What uncertainty remains,
- Which unmet needs represent the strongest product opportunities.

The output will later be used to:
1. Identify promising opportunity areas,
2. Select a target user segment,
3. Conduct 5–6 primary user interviews,
4. Validate the strongest opportunity,
5. Define the final product problem,
6. Eventually build an MVP.

**Important:** The Discovery Engine itself must **not** decide the final solution.

---

## 3. Core Research Question

> **Why does a user who has explicitly wishlisted a fashion product not purchase it within the next 30 days?**

### 3.1 Wishlist Intent

| ID | Question |
|----|----------|
| WI-1 | Why did the user save the product? |
| WI-2 | Was the wishlist created with an intention to purchase? |
| WI-3 | Was the user simply bookmarking the product? |
| WI-4 | Was the product saved "for later"? |
| WI-5 | Was the user waiting for an occasion? |
| WI-6 | Was the user comparing it with alternatives? |
| WI-7 | Was the user saving multiple similar products? |

### 3.2 Purchase Barriers (hypotheses, NOT predetermined findings)

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

These are candidate hypotheses the engine must test against real data. **The engine must discover which problems actually appear repeatedly** — it must not confirm a pre-decided answer.

---

## 4. Sources to Analyze

The engine should collect **publicly available** conversations from multiple sources.

| Source | Focus |
|--------|-------|
| App Store reviews | Shopping experience, wishlist behaviour, product discovery, purchase hesitation, fit/size, reviews, returns, quality, decision-making |
| Google Play Store reviews | Same categories, especially mobile-specific behaviour |
| Reddit | Fashion/shopping communities: Myntra, AJIO, Nykaa Fashion, online fashion shopping, wishlist behaviour, sizing, outfit decisions, comparison, shopping hesitation |
| Other (optional) | YouTube comments, fashion forums, public social-media conversations, product reviews, product Q&A, blogs |

The engine should prioritize **actual user language and experiences** over generic editorial articles about fashion commerce.

---

## 5. What the Engine Should NOT Do

- ❌ Not just: *"70% of reviews are positive and 30% negative."* That doesn't answer the business problem.
- ❌ Not just: *"Users are unhappy with size, price and quality."*

Instead, it must connect evidence to **user behaviour** and the **business metric**. For example:

> **Behaviour:** Users shortlist multiple similar dresses before buying.
> **Barrier:** They struggle to decide which one is actually suitable for their occasion.
> **Evidence:** Multiple users describe saving 3–5 similar products and comparing them outside the platform.
> **Potential impact:** Decision friction may delay or prevent wishlist-to-purchase conversion.
> **Opportunity:** Help users make a confident decision between shortlisted products.

---

## 6. Evidence Requirement

Every important insight must be traceable to actual user evidence. For every insight, store:

| Field | Meaning |
|-------|---------|
| Insight | What pattern was discovered? |
| User behaviour | What are users actually doing? |
| Barrier | What prevents them from purchasing? |
| Segment | Which users experience it? |
| Evidence | What did users actually say? |
| Source | Where did the evidence come from? |
| Frequency | How often did this pattern appear? |
| Confidence | How strong is the evidence? |

### The Three-Level Distinction (must never be conflated)

| Level | Definition | Example |
|-------|-----------|---------|
| **Said** | Verbatim user quote | "I saved it because I liked it but wanted to see other options." |
| **Inferred** | Structured behaviour | User is comparing alternatives before purchasing. |
| **Concluded** | Barrier / opportunity hypothesis | Comparison may delay wishlist → purchase conversion. |

---

## 7. Connection to the Business Metric

The engine must identify **where users get stuck** in this chain:

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

Example of a genuinely useful output:
> Wishlist added → high purchase intent → uncertainty remains → user compares alternatives → decision delayed → wishlist expires without purchase.

Valuable. Not: *"Users don't buy wishlist products."*

---

## 8. Required Discovery Pipeline (summary)

1. **Collect** — publicly available conversations from selected sources.
2. **Clean** — remove duplicates, spam, ads, bots, unrelated mentions.
3. **Identify relevant conversations** — wishlist behaviour, purchase intention/hesitation, comparison, fashion decision-making, uncertainty, shopping behaviour.
4. **Extract user behaviour** — shortlist, compare, wait, check fit/quality, seek social validation, occasion shopping, remember for later.
5. **Extract barriers** — explain why the desired behaviour did not complete. Example: "I loved the dress but wasn't sure about the size, so I saved it and kept looking." → Intent: purchase interest; Barrier: size confidence; Action: wishlist + continued browsing; Outcome: no purchase yet.
6. **Identify unmet needs** — what information, confidence, functionality, or experience was missing?
7. **Segment** — identify whether behaviour differs across groups (segments must emerge from evidence).
8. **Quantify** — counts, percentages, frequency by source and segment; separate frequency of mention from evidence of business impact.
9. **Rank opportunity areas** — frequency, severity, purchase impact, users affected, evidence strength, segment concentration, existing workaround, product leverage.

---

## 9. Final Output of This Phase

Before moving to the next parts of the graduation project, the engine must give:

- **A. Evidence database** — actual conversations with source info.
- **B. Behaviour taxonomy** — behaviours discovered from the data.
- **C. Barrier taxonomy** — reasons users postpone or avoid purchase.
- **D. User segments** — segments associated with different barriers.
- **E. Opportunity areas** — ranked on evidence and potential impact.
- **F. Evidence per opportunity** — actual supporting user conversations.
- **G. Research questions for interviews** — ready for the required 5–6 user interviews.

---

## 10. The Most Important Success Criterion

The Discovery Engine is successful if, after using it, you can confidently say:

> "I started with an unknown wishlist-to-purchase problem. I analyzed user conversations at scale, identified recurring behaviours and barriers, quantified the strongest patterns where possible, compared opportunity areas, and now know which problem I should validate with real users."

It fails if it is:
> "I analyzed 10,000 reviews and found that users have positive and negative opinions."

The first is **Product Discovery**. The second is **sentiment analysis**. This project is the first.

---

*Next file: [ARCHITECTURE_6_PHASE_PLAN.md](ARCHITECTURE_6_PHASE_PLAN.md) — solution architecture and phase-wise build plan.*