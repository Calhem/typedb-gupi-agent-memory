# Phase 6D: end-to-end evaluation, first run

Date: 2026-11-04. Branch `feature/phase-6d-evaluation`, from `main` at `1eb1a7a`. TypeDB CE 3.14.1,
typedb-driver 3.14.0, Python 3.13, Apple M2 Pro (10 cores, 16 GB). Offline: no paid API, no LLM judge,
no new download.

**This is evaluation only.** Production extraction, formation, answering, schemas and migrations are
unchanged, and so are every frozen question, gold answer and earlier result.

| File | Contents |
|---|---|
| [PLAN.md](PLAN.md) | The protocol, frozen before the runner existed, and its one amendment after the feasibility run |
| [manifest.json](manifest.json) | Dataset hashes, splits, source hashes of everything evaluated, scoring rules, hardware |
| [first-run/](first-run/) | The first full run, unchanged: raw per-question JSON for each part, and [aggregate.md](first-run/aggregate.md) generated from it |
| [feasibility/](feasibility/), [feasibility-repeat/](feasibility-repeat/) | The feasibility run and its repeat (identical apart from timings) |
| [failure-attribution.md](failure-attribution.md) | The earliest responsible stage for every failure, with traces |
| [operations.md](operations.md) | Throughput, latency, storage and incremental behaviour |

**Reproduce:**
- `uv run python -I -m gupi.benchmarks.e2e --label <new-label> --parts all` (needs TypeDB and `.data/`)
- `python -m gupi.benchmarks.e2e.report <label>` generates the aggregate tables
- `python -m gupi.benchmarks.e2e.compare <a> <b>` compares two runs

## What could be evaluated, and what could not
| System | Answers | Evidence retrieval |
|---|---|---|
| GUPI end to end (`rules:v2` → candidate store → `formation:v1` → TypeDB → v2) | D1, D4 | D1 (citations), D5, D6 (structured retriever over its claims) |
| Keyword (BM25) | D1: only the existing Phase 4 keyword heuristic | D1, D5, D6 |
| Embedding (bge-small, stored in TypeDB) | **not evaluated** (no answer generator) | D1, D5; D6 from the Phase 5 first run |
| Hybrid (with and without the structural filter) | **not evaluated** | D1, D5; D6 from the Phase 5 first run |
| Flat-triple or claim-node baseline | **not evaluated**: no fair implementation exists, and building one is out of scope | — |
| Any system, LoCoMo or LongMemEval answers | **not evaluated**: answering their free-form questions needs an LLM, which is not available without approval | — |

**About the datasets:**
- **D1** is the Phase 4 world: 11 messages and 15 questions, written by the implementer. Answer semantics
  were developed on it. It is the **only material with gold answers in GUPI's question form**, so all
  end-to-end answer accuracy comes from 15 questions that are not independent.
- **D4** (17 cases) consists of development tests only.
- **D2** (the Phase 2 held-out conversations) is the only independent text with claim-level gold. It has no
  questions.

**Which results are independent evidence:**

| Result | Material | Status |
|---|---|---|
| End-to-end answers, 13/15; contradiction, abstention, belief-time, open-role | D1 | **development** (implementer-written; answer semantics developed on it) |
| Qualification, attribution and independence, 17/17 | D4 | **development tests** |
| Extraction precision 30/30, recall 30/31; field accuracy | D3 | **development-adjacent** (implementer-written, with the extractor's scope in mind) |
| Formation recall 5/12, precision 5/5; entities 10/22 | D2 | **independent** (written before any extractor; seen once before, in 6B) |
| Retrieval; 0 candidates from 5,094 turns | D5 LoCoMo held-out | **independent** (second exposure, no tuning) |
| Retrieval on 64 questions; 0 candidates from 220,178 turns | D6 LongMemEval held-out | **independent** (second exposure, no tuning) |

Every favourable answer-level result comes from development material. The independent results all
concern formation and retrieval, and they are the unfavourable ones.

## Results
### C. Answers (D1, 15 questions)
| System | Correct | Incorrect | Missing | Abstained when it should | Unsupported definitive | Citation P / R |
|---|---|---|---|---|---|---|
| **GUPI end to end** | **13/15** | 2 | 0 | 6/6 | **0** | 0.889 / 0.889 |
| GUPI end to end, no reviewer | 13/15 | 2 | 0 | 6/6 | 0 | 0.889 / 0.889 |
| GUPI on gold claims (diagnostic) | 13/15 | 2 | 0 | 6/6 | 0 against gold; 5 on evidence with unrecorded provenance | 0.833 / 0.833 |
| GUPI Phase 4 pipeline, `rules:v1` (diagnostic) | 13/15 | 2 | 0 | 6/6 | as for gold claims | 0.833 / 0.833 |
| Keyword answer heuristic | 5/15 | 10 | 0 | 2/6 | 6 | 0.667 / 0.556 |

**By category:**
- **GUPI end to end:**
  - contradiction 2/2
  - abstention 6/6
  - belief-time ("as known on ...") 2/2
  - open-role ("who was ...") 3/3
- **Keyword heuristic:** 0/2, 2/6, 2/2 and 0/3 in the same categories.

**The two GUPI misses** are q01 (PRESUMED where the gold says TRUE) and q03 (UNKNOWN where the gold says
FALSE). Both are more cautious answers, not confident errors.
- **Recorded as unresolved evaluation disagreements, not proven gold errors.** The gold reasons as v1 did,
  and v2 deliberately reads the evidence differently. Neither side has been shown to be wrong, and no one
  independent has adjudicated them.
- **They still count as misses:** the frozen gold and scorer are unchanged. See
  [failure-attribution.md](failure-attribution.md).

**End to end differs from gold claims only on q01:**
- **The difference:** `rules:v2` reads "Since March 2025, ..." as *held since*, not as a start in March. So
  the two start statements no longer compete, and the joined period gives PRESUMED instead of UNKNOWN.
- **Predicted beforehand:** Phase 4's v2 report predicted exactly this outcome for that reading.

**Evidential qualification (D1):**
- **Standings:** every definitive end-to-end answer rests on *direct* evidence (8 direct, 6 not applicable,
  1 none).
- **The gold-claim configurations:** their 5 "definitive on evidence not direct" are legacy claims with no
  recorded provenance ("unrecorded"), not hedged evidence. The rule counts them by design.
- **Attribution:** D1 has no reported speech, so attribution is not exercised. It is tested only in D4.

**D4, development tests only, through the candidate store:**

| Measure | Result |
|---|---|
| temporal answers | 17/17 |
| qualification | 17/17 |
| attribution | 17/17 |
| independence of originators | 17/17 |
| citations | 17/17 |
| unsupported definitive answers | 0 |

These match the Phase 6C first run through `form()`. They are not independent evidence.

### B. Evidence retrieval
**D1** (message units, the 9 questions with gold evidence; with only 11 messages, recall@10 is nearly
guaranteed):

| System | R@1 | R@5 | R@10 | P@5 |
|---|---|---|---|---|
| keyword | 0.278 | 1.000 | 1.000 | 0.267 |
| embedding | 0.444 | 1.000 | 1.000 | 0.267 |
| hybrid-unfiltered | 0.389 | 1.000 | 1.000 | 0.267 |
| hybrid | 0.278 | 0.889 | 0.889 | 0.244 |
| structured | 0.222 | 0.389 | 0.556 | 0.133 |

GUPI's citations are an unranked set, so they are reported differently:
- **Set precision** 0.889 and **set recall** 0.889.
- **Of the 12 gold evidence messages:** 11 were cited, and 1 was formed but not cited (q03's w1-5, which
  v2 judges does not decide the queried instant). None was a stored candidate only, and none was in the
  original text only.
- **Comparing them:** these figures are not comparable with recall@k. Text retrievers must rank all 11
  messages; GUPI cites only the claims that decide the answer.

**D5, LoCoMo held-out** (1,676 scored questions, turn units). This is retrieval only, not a LoCoMo score.

| System | R@1 | R@5 | R@10 | P@5 | MRR | p50 latency |
|---|---|---|---|---|---|---|
| keyword | **0.290** | **0.502** | **0.565** | **0.114** | **0.416** | 0.043 s |
| hybrid-unfiltered | 0.218 | 0.469 | 0.565 | 0.108 | 0.368 | 0.114 s |
| hybrid | 0.217 | 0.428 | 0.511 | 0.101 | 0.350 | 0.186 s |
| embedding | 0.140 | 0.363 | 0.465 | 0.084 | 0.270 | 0.071 s |
| GUPI structured (over its formed claims) | 0.001 | 0.011 | 0.038 | 0.003 | 0.015 | 0.074 s |

R@5 by category (keyword / hybrid-unfiltered / GUPI structured):

| Category | Questions | keyword | hybrid-unfiltered | GUPI structured |
|---|---|---|---|---|
| temporal | 257 | 0.561 | 0.546 | 0.012 |
| multi-hop | 239 | 0.154 | 0.184 | 0.004 |
| adversarial | 375 | 0.588 | 0.565 | 0.000 |
| single-hop | 727 | 0.579 | 0.514 | 0.019 |
| open-domain | 78 | 0.241 | 0.193 | 0.003 |

On multi-hop, the structure-filtered hybrid is the best of all systems, at 0.200. **All 8,380 rows are
identical to the Phase 5 first run.**

**D6, LongMemEval held-out subset** (64 questions; session R@5 / turn R@5):

| System | Session R@5 | Turn R@5 |
|---|---|---|
| keyword | 0.836 | 0.653 |
| GUPI structured | 0.000 | 0.000 |

- **Identical to Phase 5:** all 254 rows match Phase 5's first run.
- **From Phase 5's first run on the same 64 questions:**

| System | Session R@5 | Turn R@5 |
|---|---|---|
| embedding | 0.933 | 0.618 |
| hybrid | 0.923 | 0.685 |

**Where the evidence sat** (the GUPI arm, D5 and D6). For every scored question, the gold evidence stayed
only in the original text:
- **No candidate was extracted** from any gold turn, so the earliest stage is "extraction missed" for
  1,676/1,676 LoCoMo and 63/63 LongMemEval questions.
- **LoCoMo's 2,425 gold evidence turns (counted once per question):** 2,187 are outside the extractor's domain (it reads only employment and
  reporting lines), and 238 contain a domain verb in a sentence it could not parse.

### A. Memory formation
| Measure | D2 independent | D3 implementer-written |
|---|---|---|
| candidate precision | 5/5 | 30/30 |
| candidate recall | **5/12** | 30/31 |
| entities (participants) precision / recall | 10/10 / 10/22 | — |
| relation: extracted with the right type and roles | 5/5 | 30/30 |
| temporal: start exact / end and ongoing exact (of matched) | 4/5 / 5/5 | 12/30 under the frozen 6B convention |
| polarity, modality, commitment, attribution, asserted-by (of matched) | all positive, actual, direct in this gold | 30/30 each |
| policy decisions: formed / withheld / review / rejected | 5 / 0 / 0 / 0 | 20 / 4 / 6 / 0 |
| gold claims as accepted claims in TypeDB / stored candidates only / absent | 5 / 0 / 7 | 20 / 10 / 1 |
| LoCoMo held-out (5,094 turns) | 0 candidates | |
| LongMemEval held-out (220,178 turns; 816 answer turns) | 0 candidates | |

**Notes on these figures:**
- **The D2 start miss is a convention difference.** "Has worked at Vector since 2022": the Phase 2 gold
  encodes it as a start in 2022, while `rules:v2` records only that it held by the end of 2022.
- **D3's 10 stored-only candidates are kept by design:**
  - 4 withheld: 3 plans and 1 forwarded copy
  - 6 waiting for review: 3 hedged, 2 corrections, and 1 time phrase that could not be read
- **D1 end to end:** the policy formed all 11 candidates, and the simulated reviewer acted once (rejecting
  w2-1's claim).

### D. Operations (details in operations.md)
**Ingestion costs:**

| Measure | Value |
|---|---|
| `rules:v2` extraction | about 26,600 short turns/s (LoCoMo), 7,200 long turns/s (LongMemEval) |
| Store submission | about 23 ms per observation with candidates, flat up to 992 observations |
| Turn ingestion | about 190 turns/s (LoCoMo) |
| Embedding | about 53 short turns/s |

**Storage:** LoCoMo held-out takes 24.7 MB without embeddings and 59.1 MB with them. The candidate store
adds about 5 KB per observation.

**Query costs:**

| Measure | Value |
|---|---|
| v2 answer latency | p50 about 0.025 s, p95 about 0.06 s (D1); flat as the store grows |
| `store.pending()` | grows linearly, from 0.023 s at 120 candidates to about 0.2 s at 930 (S4) |
| Resubmitting | writes nothing |

## Assessment
**Where GUPI does better.** These results come from D1 and D4, which are small and not independent.
- **Against text-only answering** (the keyword heuristic), GUPI wins on the questions its design targets:
  - when a statement held (valid time)
  - what was known when ("as known on ...")
  - contradictions answered as CONTESTED, not resolved
  - abstention instead of a guess, and no definitive answer the evidence does not support
- **The size of the gap:** 13/15 vs 5/15, 6/6 vs 2/6 abstentions, and 0 vs 6 unsupported definitive
  answers. Its citations point at the deciding statements.
- **The hedged and reported evidence of D4** is qualified, never presented as definitive.

**Where it does equally well.**
- End to end matches GUPI on gold claims (13/15 each) on D1. Its phrasings fall inside `rules:v2`'s
  coverage, so extraction cost nothing there. This does not generalise (see below).
- LoCoMo and LongMemEval retrieval are unchanged from Phase 5, because no claims were formed.

**Where it does worse.**
- **On natural conversation, GUPI's structured path finds almost nothing:**
  - LoCoMo R@5 0.011, against keyword 0.502
  - LongMemEval 0.000, against keyword 0.836 and embedding 0.933 at session level
- **Why:** extraction produced no candidates from 225,272 turns.
- **On independent organisational text** (D2), only 5 of 12 gold facts reached memory.
- **What GUPI answers at all:** only typed employment and reporting questions about named people. None of
  LoCoMo's or LongMemEval's questions can be put to it.

**What can be attributed to what.**
- **GUPI's overall methodology:** all of the D1 and D4 advantages come from its methodology:
  - claims kept apart from observations, with valid and belief times
  - review and formation decisions recorded per candidate
  - evidence-first v2 semantics with abstention
  - evidential standing kept separate from truth
  - deterministic validation
- **TypeDB specifically: none shown.** No same-logic comparison on another store was run (none exists).
  TypeDB holds and queries the data correctly and fast enough at this scale, and functions such as
  `believed_at` run in it. But nothing here shows that this beats the same design on, say, PostgreSQL
  plus Python.
- **What simpler representations could plausibly reproduce: probably all of the measured advantages.** The
  answers depend on per-claim valid and recorded times, review events, provenance fields and v2 rules
  that are written in Python. A flat claim table with those columns, plus the same Python logic, would
  plausibly score the same on D1 and D4. Typed n-ary roles were not stressed: every D1 relation is binary.

## The three most consequential technical limitations
1. **Extraction coverage is the bottleneck.**
   - **The evidence:**
     - 0 candidates from 225,272 LoCoMo and LongMemEval turns
     - 5/12 recall on independent organisational text
     - "extraction missed" is the earliest failed stage for every LoCoMo and LongMemEval question
   - **What follows:** every downstream advantage applies only to the evidence that reaches memory.
2. **The question interface is narrow.**
   - **The constraint:** GUPI answers only typed questions (claim type, named role players, an instant).
   - **The consequence:** there is no route from a natural-language question to that form, and none to a
     final answer. So no public end-to-end benchmark can be scored, and the answer-level evidence is 15
     non-independent questions.
3. **Formation forms direct assertions without a reviewer.**
   - **The behaviour:** the store's review path is exercised only for hedged, corrected or unreadable
     statements.
   - **In D1:** the policy formed w2-1 and w2-3, which the world records as rejected and never reviewed.
     No frozen question asks about them at a time they cover, so the scores cannot show the effect.
   - **Related:** unauthenticated reviewer names (S7) and the linear `pending()` scan (S4, now measured) are
     smaller but real.

**Correctness defects found: none.**
- **What this rests on:** nothing in this run contradicts the documented semantics or policy. The two
  misses follow approved decisions (ADR 0009 Q1 and joined spells as PRESUMED).
- **So:** no regression test is proposed.
- **For the owner to decide:** whether formation:v1's auto-forming of plain direct assertions (limitation 3)
  should stay the default.

**Recommended next priority:** extraction that produces candidates from natural, independent text,
measured first on fresh independent material, before more work downstream. Two possible routes:
- a local model
- the approved Claude extractor within the $10 ledger, which needs the owner's approval

Next after that, a route from natural-language questions to GUPI's typed questions, so that a public
benchmark can be scored end to end.
