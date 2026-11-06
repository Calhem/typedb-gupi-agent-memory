# Phase 8A, part 4: evaluation protocol

## 1. What the feasibility probes already show
**Development data only.** Read-only, run outside the database, with a keyword replica that reproduces the committed
baseline exactly (0.513 and 0.587). Eight variants were tried on 301 LoCoMo questions, so the best is an optimistic
estimate. Full output: [probes/results.txt](probes/results.txt).

**LoCoMo development, turn recall** (`structure` = keyword hits, their neighbouring turns, and the named speaker's
turns, interleaved):
| Category (questions) | Keyword R@5 | `structure` R@5 | Keyword R@10 | `structure` R@10 |
|---|---|---|---|---|
| multi-hop (42) | 0.132 | **0.187** | 0.195 | **0.301** |
| single-hop (114) | 0.500 | 0.548 | 0.548 | 0.737 |
| temporal (63) | 0.762 | 0.794 | 0.825 | 0.857 |
| adversarial (71) | 0.599 | **0.556** | 0.711 | 0.775 |
| open-domain (11) | 0.136 | 0.182 | 0.318 | **0.273** |
| all (301) | 0.513 | 0.538 | 0.587 | 0.693 |

**What each idea contributed:**
| Variant | Multi-hop R@10 | Verdict |
|---|---|---|
| Named-entity bridges between turns | 0.199 | **drop.** Only 12% of multi-hop gold turns contain a usable entity. The mention layer it would need is not worth building |
| Pseudo-relevance feedback (text-only control) | 0.168 | drop; shows the gain is not just more words |
| Neighbouring turns | 0.233 | keep. Single-hop R@10 0.548 → 0.746. Often the answer is the reply to the matched turn |
| Named speaker first | 0.267 | keep, **never as a filter**: adversarial R@5 halves (0.599 → 0.303) because those questions name the wrong speaker |
| Interleaved (`structure`) | **0.301** | proposed starting point |

**LongMemEval development:** neighbouring turns gave **no gain** (session R@5 0.923 unchanged; turn R@10 0.867 →
0.806). Multi-session is 8 scored questions. Keyword already reaches 0.923 at session level, so there is little room.

**Three honest limits:**
1. The +10.6 points at R@10 is **below the 15-point stretch target**, and +5.5 at R@5 further below it.
2. On 42 questions, one question moves R@10 by about 2 points.
3. **This is not yet a TypeDB advantage.** Authorship and turn order would work in any store. The claim that TypeDB's
   relationships add something must be tested on claim paths, which is why §2 has two tracks.

## 2. Two tracks, because they answer different questions
| Track | Question | Data |
|---|---|---|
| **R, relationship** | Do TypeDB claim paths retrieve connected, qualified evidence that text cannot? | a new fixture, G1 |
| **C, conversation** | Does structure help on real chat without hurting simple recall? | LoCoMo and LongMemEval development |

**G1 (new fixed development set).** A small synthetic world of about 80 messages and 60 questions, frozen and hashed
before any retrieval code, in the Phase 4 style:
| Class | Questions | Tests |
|---|---|---|
| simple recall | 12 | no regression |
| multi-hop | 16 | paths of 2 claims, some of 3 |
| historical and temporal | 12 | spells, gaps, reinstatement |
| corrections and conflict | 10 | supersession, disputes, pending retraction |
| identity ambiguity | 10 | same names, first names, aliases |

- **Gold:** the supporting observations, the claim path where one exists, and the expected temporal label.
- **Extraction:** claims come from recorded developer responses through `model:candidate-v1.1`, plus a gold-claims
  configuration, so extraction errors can be separated from retrieval errors.
- **Split:** 40 development, 20 sealed for one run after the code is frozen.
- **Weakness:** it is implementer-written, so it can show a mechanism works, not that it generalises. An
  externally written set (R10) remains the better test, and is an owner decision.
- **Not used:** the Stage 3 corpus and gold stay frozen and private.

## 3. Systems under one budget
| | System | Notes |
|---|---|---|
| A | keyword | `evidence.keyword` |
| B | current GUPI | hybrid, hybrid-unfiltered and structured, as frozen |
| C | keyword + structure | neighbours and speaker, no claims |
| D | keyword + structure + claim paths | the proposal |
| E | D + embeddings | optional; only if the existing local model is already present, with no download |

**All systems:** same questions, same scope, same k (5 and 10), same gold, same scorer. C and D differ by exactly one
component, so a gain can be attributed.

## 4. Metrics, always by class
| Metric | Definition |
|---|---|
| Evidence recall@k, precision@k | existing scorer; precision is new and uses the same gold |
| Path completeness | share of questions with **every** gold item in the top k |
| Evidence correctness | returned claims are in the right tier: no retracted or disputed item as `accepted` |
| Temporal correctness | hop labels equal gold labels; **zero** invented `confirmed` overlaps is a hard requirement |
| Identity conflation | paths joining distinct gold entities; **zero** is a hard requirement |
| Provenance correctness | correct source and asserter on each hop |
| Added uncertainty | `unresolved` items per question, and the share that are relevant |
| Latency | median and p95 per question, reported separately for each stage |
| Answer accuracy | where feasible: G1 deterministic labels first. LLM-graded answers only after a decision (part 5 §4) |

## 5. Stop conditions
| Condition | Action |
|---|---|
| **Hard:** any invented overlap, conflation, or uncertain item shown as accepted | fix before anything else; no score counts until zero |
| Track C single-hop R@5 falls more than 1 point against keyword | fix the ranking; do not raise budgets |
| Track C adversarial R@5 falls more than 5 points | stop, and report the trade-off for a decision |
| Track R: D beats C on multi-hop path completeness by **less than 10 points** | **TypeDB's relationship contribution is not shown.** Diagnose (extraction, query, or ranking), report, and add no complexity |
| Track C: the stretch target is missed | expected; report the number. It is not a failure by itself |
| Latency p95 above 250 ms at 10,000 claims | stop adding hops |
| Fixture questions pass only with hand-fixed claims | report as an extraction limit, not a retrieval result |

## 6. Rules against fooling ourselves
- **No held-out use during development.** LoCoMo and LongMemEval held-out sets and the sealed G1 questions are untouched
  until code and configuration are frozen and the owner approves one run.
- **Pre-register.** `benchmarks/config.json` is frozen. New systems go in a new config, committed before scoring.
- **Report first runs unchanged,** including failures, by category, not just overall.
- **Licence:** LoCoMo is CC BY-NC 4.0, and its commercial status is unresolved (`docs/known-issues.md`). Only aggregates
  are committed, and results stay out of external claims until the owner resolves it.
