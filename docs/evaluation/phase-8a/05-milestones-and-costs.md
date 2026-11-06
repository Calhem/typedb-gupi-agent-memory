# Phase 8A, part 5: milestones, costs, risks and decisions

## 1. Milestones
Each ends with a stop for review. Stop conditions come from part 4 §5.

### 8B: relationship-aware retrieval
| | |
|---|---|
| **Deliverable** | `gupi/paths.py`: seeds, structural neighbours, Q1–Q6, ranking, budgets, `EvidenceSet`. Benchmark systems C and D. G1 frozen first |
| **Tests** | budgets and truncation; determinism (same input, identical output); hub rule; no regressions; synthetic fixtures only |
| **Success** | D beats C by at least 10 points on G1 multi-hop path completeness; Track C single-hop R@5 within 1 point of keyword; p95 under 250 ms at 10,000 claims |
| **Stop if** | D does not beat C: diagnose before 8C |

### 8C: temporal and provenance integration
| | |
|---|---|
| **Deliverable** | per-hop labels from `classify`, Q7–Q8, tiers, belief-time seeds, retraction targets stored as suggestion targets |
| **Tests** | gaps and reinstatement; disputes; pending retraction; allegations through paths; recorded versus valid time |
| **Success** | G1 temporal and correction classes: zero invented overlaps, labels at least 90% correct, provenance at least 95% correct |
| **Decision** | event type (part 3 §3), with measured impact |
| **Stop if** | labels need a new temporal concept: report, do not build one |

### 8D: identity and ranking
| | |
|---|---|
| **Deliverable** | conservative anchors, deduplication across aliases, ranking tuned on development data only |
| **Tests** | same names, first names, accepted and rejected identities, as-of behaviour |
| **Success** | G1 identity class: zero conflation; recall gain from accepted aliases measured |
| **Stop if** | gain under 2 points on development data: drop it. Ranking stays simple |

### 8E: benchmark and leaderboard integration
| | |
|---|---|
| **Deliverable** | verified leaderboard rules; thin `add` and `search` adapter; confirmation run |
| **First step** | **verify** the leaderboard, models, protocol and submission conditions. No integration before that |
| **Tests** | adapter contract; an end-to-end smoke test; cost ceiling agreed first |
| **Success** | one approved held-out run, reported unchanged, by category |
| **Stop if** | the rules need something GUPI cannot do honestly, such as losing qualifications |

### Remove or defer
| Feature | Recommendation | Why |
|---|---|---|
| Named-entity turn bridges, a mention spotter | **remove** | measured no gain: 0.199 against 0.195 |
| Pseudo-relevance feedback | **remove** | measured worse |
| Author-based hard filter | **remove** | halves adversarial recall |
| Question-type router | defer | always-on light expansion is simpler; add only if latency needs it |
| TypeQL functions, recursive identity | defer | no measured need |
| Embeddings in the first comparison | defer to optional | keyword is stronger here; adds cost |
| Three-hop traversal | **do not build** | start from a seed passage in the middle instead |
| A broader typed domain (projects, events) | defer | `statement` already carries these |

## 2. Expected complexity, performance and cost
| Item | Estimate |
|---|---|
| New code | about 300 lines of Python, one module; no new dependency or service |
| Schema | none for 8B |
| One hop | 1–28 ms median (hub, capped) |
| Two hops | 8 ms ordinary; 36 ms through a hub (p95 65 ms), capped at 200 paths |
| Full claim views | 12 ms for 50 claims |
| Expected per-question total | under 150 ms (*estimate*: sum of stages, plus 50 ms keyword) |
| Keyword today | 25 ms median on LoCoMo; 175 ms on LongMemEval development |

**Measured** on 2,649 claims, 5,298 mentions and 1,600 referents, on one laptop, with a hub holding a third of all
employment claims (`probes/results.txt`). 10,000 claims is a later check, not a measured result.
**Paid costs in 8B–8D:** none.

## 3. Risks
| Risk | Severity | Handling |
|---|---|---|
| **Extraction recall on chat.** No claims means no paths: LoCoMo still has 0. **This is the largest risk.** Structure helps without claims, but TypeDB's real contribution on chat needs claims | high | Track C does not depend on it; §4 decision 2 |
| The only strong evidence for paths comes from an implementer-written fixture | high | sealed questions; label results as development; R10 |
| Temporal: a path reads as simultaneous | high | hop labels; hard stop condition; part 3 §2 |
| Ambiguous identity | high | never merge; hard stop condition |
| Hub expansion | medium | hub rule, caps, `truncated`; measured under 70 ms |
| Tuning to 42 multi-hop questions | medium | eight variants disclosed; confirm once on held-out |
| Older `ClaudeExtractor` path bypasses R1–R3 | medium | use `model:candidate-v1.1` only |
| Pending retraction cannot reach its claim | medium | 8C targets; Q7 in the meantime |
| More evidence crowds out the best evidence | medium | keyword slots protected; precision reported |
| LoCoMo licence | medium | aggregates only; no external claims |

## 4. Decisions needed from the owner
1. **Which leaderboard?** The repository names none, so its rules, models, Add/Search shape and conditions are unverified.
2. **Where do chat claims come from?** Without them, Track R stays on the fixture. Options:
   | Option | Cost | Note |
   |---|---|---|
   | stay structure-only for chat | none | simplest; the TypeDB case rests on the fixture |
   | subscription session on development conversations, as in Stage 3B | $0, manual | proves value; not repeatable for a leaderboard |
   | paid automated extraction | needs a budget | what a real `add` would need; through `gupi.budget.Ledger` |
   | local model | a download | currently not allowed |
3. **Who writes G1?** Me, for speed, or someone outside the project, for credibility.
4. **May the carried-over items wait?** Item 9, R4, R5, S8 and L4 are not needed for 8B. *Recommended: yes.*
5. **Is the adversarial trade-off acceptable?** Development shows R@5 −4.3 with R@10 +6.4.
6. **Event type in 8C?** Decide with measured impact.
7. **Answer-level evaluation:** needs an LLM answerer. Paid, or manual, or deferred to 8E?
8. **Does the 0.460 embedding figure come from a run I cannot see?** If not, use 0.342.
