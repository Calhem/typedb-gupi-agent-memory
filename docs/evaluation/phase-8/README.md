# GUPI Phase 8B: relationship-aware retrieval results

**Status (2026-11-06): implemented and evaluated. Not merged.** Branch `feature/phase-8b-relationship-retrieval`, from
Phase 8A (`82736be`). No paid call, model download, schema change, or held-out data.

**None of this is a leaderboard or benchmark result.** LoCoMo and LongMemEval figures are development data. The
claim-path fixture is developer-authored and exploratory.

## The answer
**Did TypeDB's structured claims retrieve evidence that simpler methods miss? Not on the primary measure.**

| Question | Answer | Evidence |
|---|---|---|
| **A. Does conversational structure help?** | **On LoCoMo yes; on LongMemEval no** | LoCoMo R@10 0.587 → 0.698; LongMemEval turn R@10 0.867 → 0.857 |
| **B. Do claims add recall beyond it?** | **Not shown** | multi-hop R@10, C over B: +18.2 points on development, **0 on sealed**. A text-only name-matching control **equalled C at R@10 on both** |
| **C. Do temporal correctness and integrity hold?** | **Yes, after one fix** | no severe failures; one sealed check failed, was diagnosed and fixed; 28 of 28 pass now; 7 temporal regressions pass |

**What claims did contribute, measured:**
1. **Order at a tight budget.** At R@5, C beat B and the control on both question sets.
2. **What the evidence means.** C alone says who asserted it, whether it is accepted, disputed or pending, and whether
   two relationships held together. The control returns bare text and cannot do any of that.

So the supported claim is narrow: **TypeDB's claims make connected evidence more trustworthy and better ordered. They
have not been shown to find evidence that name matching cannot.** The fixture is small and full of names, which suits
the control. A name-sparse fixture is the fairer next test.

## Comparison on the frozen fixture
57 claims in 71 messages. `A` keyword, `B` + conversational, `C` + claim paths, `C1` one hop only, `D` text-only name
control, added after the fixture froze and before the sealed run. Same budget throughout.

| Multi-hop | A | B | C | C1 | D |
|---|---|---:|---:|---:|---:|
| **Development (11), R@10** | 0.742 | 0.697 | **0.879** | 0.879 | **0.879** |
| Development, R@5 | 0.667 | 0.621 | **0.712** | 0.667 | 0.576 |
| Development, path complete@10 | 0.455 | 0.364 | 0.727 | 0.727 | 0.727 |
| Development, path complete@5 | 0.364 | 0.273 | **0.455** | 0.364 | 0.182 |
| Development, precision@10 | 0.155 | 0.145 | 0.182 | 0.182 | 0.182 |
| **Sealed (5), R@10** | 0.800 | **0.900** | **0.900** | 0.900 | **0.900** |
| Sealed, R@5 | 0.700 | 0.800 | **0.900** | 0.800 | 0.500 |
| Sealed, path complete@5 | 0.400 | 0.600 | **0.800** | 0.600 | 0.000 |

**Other classes:** simple recall 1.000 for all systems on both sets, so no regression. Temporal development R@10: B 0.929,
C 0.964, D 0.881. Correction development R@5: B 0.750, C **0.500** (A 0.500). Negative development R@10: A and D 1.000, B and C
**0.750**. All sealed non-multi-hop classes scored 1.000 for every system, so they do not separate anything.
**Compared with keyword alone,** C's development multi-hop R@10 gain is 13.6 points, smaller than the 18.2 over B,
because B itself fell below A on this fixture.

**Sample sizes are very small:** one sealed question moves multi-hop recall by up to 20 points.

**Real conversations:** LoCoMo still produces 0 claims. On LoCoMo and LongMemEval development C equals B on every
question (301 and 102 rows), costing about 15 ms and 75 ms extra at p50.

## Integrity
| Check | Result |
|---|---|
| Severe failures (uncertain shown as accepted, hop with no evidence) | **0** on both sets |
| Scored checks | development 18/18; sealed **9/10 on the single run**, 10/10 after the fix |
| Temporal regressions | all 7 pass: before and after departure, unknown intervals, reinstatement, conflicting dates, explicit versus inferred, never simultaneous |
| Allegations, reports, disputes, pending retractions | all stay visible on the item, the hop and the rendered text |
| Formation and correction policy | unchanged; no review item approved |

**The sealed failure:** `g27`, a path labelled `unknown` one way and `none` the other. It was a real defect, though a safe
one, since it invented nothing. Fixed in `5e2c661`; no recall figure changed.

**Defects found by inspection, not by the scoring:** identity claims treated as evidence, which marked plain facts
"provenance not recorded"; duplicate items; a pending retraction on an unrelated claim; second hops not following
accepted identity; hops staying `accepted` under a pending retraction. All fixed with tests before the sealed run. **The
scored checks passed 18/18 while these existed, so the checks are weaker than that number suggests.**

## Why C missed what it missed
| Cause | Questions | Note |
|---|---|---|
| **Ranking:** the evidence was in a path, but cut by the budget | g11, g18, g26, g31, g44, g19 (6) | the largest cause. Not tuned here: ranking belongs to 8D |
| **Path cap:** the walk's 50 paths ran out first | g52 | a hub-like company |
| **Missing event representation** | g56 | a withheld one-time event cannot be a hop |
| Three-claim questions | g11 | two hops cannot span three claims from one start |

**Event gap, for 8C:** 2 of 47 fixture candidates were withheld for this reason, and 2 of 60 questions depend on them.
On this evidence the event gap is not the main limit. It would matter more where events dominate.

## Performance
| | p50 | p95 |
|---|---|---|
| LoCoMo: keyword / conversational / with claim layer (no claims) | 21 / 60 / 74 ms | 31 / 72 / 88 ms |
| LongMemEval: same | 110 / 191 / 267 ms | 277 / 363 / 447 ms |
| Fixture: keyword / conversational / claim paths | 6 / 18 / 74–82 ms | 9 / 22 / 122–152 ms |

Bounded and predictable at this scale. Not measured at production size.

## What was built
| File | Lines | Purpose |
|---|---|---|
| `src/gupi/paths.py` | 456 | the module |
| `src/gupi/memory.py` | +5 | `Memory.retrieve` |
| `src/gupi/benchmarks/phase8.py`, `phase8_paths.py` | 376 | development runners; neither can read held-out data |
| `benchmarks/phase8b.json` | | the frozen configuration for these runs |
| `tests/fixtures/phase8b/` | | frozen fixture, scoring rules, hashes |
| tests | 40 new | 9 database-free (ordering is pure), 31 on TypeDB |

**`paths.py` is 456 lines against a 300-line guide.** The excess is integrity, not traversal: qualification, pending
retractions, disputes and text rendering take roughly a third of the file. No new dependency, service or schema change.

**Public interfaces:** additive only. `Memory.retrieve()`; `paths.retrieve`, `conversational`, `render`, `Budget`.

**TypeDB queries added** (all in `paths.py`): `MEMBERS`, `AUTHORS`, `SEED_REFERENTS`, `HOP`, `REFERENT_LABELS`,
`OBSERVATION_CLAIMS`, `OBSERVATION_DECISIONS`, `AUTHOR_OF`, `TEXT`, `THREAD_RETRACTIONS`. A single two-hop query, as Phase 8A
proposed, **could not be used:** referents are per conversation, so crossing threads needs identity groups between hops.
Hops therefore run as two batched queries, with Python following accepted identities.

**Temporal and integrity compatibility:** the temporal model is unchanged and authoritative (`classify`). Traversal does
not filter by time, because a spell can span two claims. Claims come only through `model:candidate-v1.1`, the store and
`formation:v1`. The older `ClaudeExtractor` path is not used. Belief time is honoured, including the `received-at` gap
in `evidence.keyword`, which itself stays frozen.

## Frozen artefacts and checks
| Check | Result |
|---|---|
| Full suite with TypeDB | **619 passed, 19 expected failures, 0 skipped** |
| Fixture hashes | all verify |
| `benchmarks/config.json`, `split.json`, Phase 5 and 7B results, schema, formation, extraction, temporal, `evidence.py` | unchanged since `main` |
| Stage 3 gold and private repository | hash matches, clean |
| Public diff | no LoCoMo text (0 of 7,616 strings), no LongMemEval questions, no Stage 3 gold, no paths or secrets |

**Fixture discrepancies, left as frozen:** the split came out 41 development and 19 sealed, and the world has 71 messages;
the README planned 40, 20 and about 80. `C1` and `D` were added after freezing, before the sealed run.

## Remaining limitations
- **Claims on real chat do not exist.** C equals B on both benchmarks. Everything about C rests on a small fixture written
  by the same agent as the code. **This shows claim traversal works when claims exist, not that GUPI can create them.**
- **Downstream answer accuracy was not measured.** It needs an LLM and so paid calls or a manual run.
- **LongMemEval got slightly worse** with conversational structure, and the default still enables it.
- **Identity:** claims connect across conversations only through accepted identities. Sessions under one AML `user_id`
  would be disconnected unless scoping or acceptance changes. **This is a design issue for any automated pipeline.**
- **Disputes come back UNKNOWN, not CONTESTED,** so they are shown through both sources.
- **Retraction detection is lexical,** and pending notes are limited to the same thread and author.
- **`explicit` dates** remain in the candidate; retrieval does not display them yet.
- **Latency is measured on a small database.**

## Recommendation: revise, then proceed
**Do not move to 8D or 8E yet.** The primary target was met on development and missed on sealed, and the control means
even the development gain cannot be credited to typed claims.

**8C should change focus. In order:**
1. **Settle where chat claims come from.** Nothing else matters as much. Under AML's open-source rules that means
   `gpt-4o-mini` during Add, so its extraction quality through the protected pipeline must be measured. This needs budget
   approval.
2. **Run a harder, fairer test:** an independently written, name-sparse fixture of at least 50 multi-hop questions, keeping
   the name control, at depths including AML's 100.
3. **Decide session-spanning identity,** which AML's `user_id` scope forces.
4. **Measure answer accuracy,** since AML scores answers. The evidence-integrity value is unproven until a model uses it,
   and AML's fixed prompt says to prefer the most recent memory when memories conflict.
5. **Defer:** the event type, TypeQL functions, and a ranking overhaul, until 1–4 show they matter.

**Stop condition for 8C:** if claims extracted automatically from real conversations give no measurable gain over B and
the control, keep GUPI's evidence layer as a qualification feature, and do not claim a retrieval advantage from TypeDB.

**AML:** Cycle 2 has closed and no next cycle is announced. See [leaderboard-requirements.md](leaderboard-requirements.md).
