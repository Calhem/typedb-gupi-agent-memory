# Phase 8F: activity consolidation validation

**One development conversation. No human annotator was involved. Every ledger came from a Claude model, under one subscription, so separate agents are not independent people. Agreement is not accuracy: there is no gold. Not a benchmark or leaderboard result.**
Numbers: [agreement](results/8f-agreement.json), [post-hoc](results/8f-post-hoc.json). Ledgers are private. Rules: [protocol](protocol.md), fixed at `a79fe9b` before any reader ran.

## Who produced what
| Ledger | Producer | Activities | Mentions |
|---|---|---:|---:|
| A | Claude Opus 5.5, the session that built GUPI, Phase 8E | 17 | 81 |
| B | fresh Claude Sonnet 5.5 agent, annotation manual | 27 | 73 |
| C1 | fresh Claude Sonnet 5.5 agent, fixed specification | 16 | 72 |
| C2 | fresh Claude Haiku 5.5 agent, fixed specification | 9 | 47 |

**Isolation.** Each agent's tool calls were audited from its transcript. Each read only its own folder and wrote only its own ledger. No agent saw another's output.

**A disclosed leak path.** Agents automatically receive my memory index. *Corrected in Phase 8G:* I had removed the line mentioning the Phase 8E conclusion, but subagents receive a cached copy, so that made no difference. These agents were clean because their cached copy was older and held no conclusion, which their transcripts confirm.

**A known bias.** I wrote the annotation scheme, so all readers share its vocabulary. And C1 and C2 share one specification, which helps them agree.

## Verdict against the frozen criteria
| Criterion | Measure | Threshold | Result | |
|---|---|---:|---:|---|
| **1. Reproducible** | mention F1, A with B | 0.70 | 0.714 | pass |
| | activity F1, A with B | 0.60 | 0.591 | **fail** |
| | adjusted Rand, A with B | 0.70 | 0.527 | **fail** |
| | B-cubed F1, A with B | 0.75 | 0.790 | pass |
| **2. Merges and continuity** | merge rate, A with B | at most 0.15 | 0.091 | pass |
| | invented continuity | 0 | 1 in each of B, C1, C2 | **fail** |
| **3. Provenance** | valid evidence | at least 98% | 100% in all four, 192 of 192 new mentions | **pass** |
| **4. Temporal ambiguity** | final-state kappa, A with B | 0.60 | 0.711 | pass |
| | known conflict reported by each | all | all | pass |
| **5. Automation** | C1 mention F1 and adjusted Rand, against A and B | 0.70 | 0.72 and 0.78; 0.76 and 0.78 | pass |
| | correction share | at most 0.30 | 0.31 against A, 0.13 against B | **narrow fail** |

**Criteria 3 and 4 pass. Criteria 1, 2 and 5 do not.** Under the rule fixed in advance, full activity modelling is not recommended. Near misses stay misses.

## Reader agreement
| Pair | Mention F1 | Activity F1 | Adjusted Rand | B-cubed F1 | Role kappa | Link kappa | State kappa |
|---|---:|---:|---:|---:|---:|---:|---:|
| A, B | 0.71 | 0.59 | 0.53 | 0.79 | 0.70 | 0.03 | 0.71 |
| A, C1 | 0.72 | 0.79 | 0.78 | 0.87 | 0.72 | 0.28 | 0.24 |
| A, C2 | 0.61 | 0.69 | 0.69 | 0.85 | 0.63 | 0.84 | 0.45 |
| B, C1 | 0.76 | 0.70 | 0.78 | 0.88 | 0.79 | 0.03 | 0.69 |
| B, C2 | 0.60 | 0.33 | 0.69 | 0.82 | 0.77 | 0.11 | 1.00 |
| C1, C2 | 0.67 | 0.72 | 0.91 | 0.95 | 0.85 | 0.28 | 0.85 |

**What the numbers mean:**
- **Granularity is the main disagreement.** 9 to 27 activities for one conversation. Mostly it's one reader splitting what another keeps together, not readers contradicting each other. Nothing defines the right level.
- **A fixed specification helps a lot.** C1 and C2, different models, agree at 0.91. A manual leaves more freedom. Shared instructions partly explain that.
- **Roles are reasonably stable.** Kappa 0.63 to 0.85.
- **Per-mention certainty isn't reproducible.** Link kappa is near zero for most pairs. "Clear" and "probable" don't mean the same to different readers.
- **C2 found far less:** 47 mentions, with recall of 0.62 on what A and B agree on. The cheaper model is safe but thin.

## Automated consolidation
There is no defensible gold. The floor is **what A and B agree on**: 55 mentions, 76 links within activities, and 1,294 pairs both kept apart. Everything else is undecided.
| | Mentions recovered | Agreed links recovered | Agreed separations broken |
|---|---:|---:|---:|
| C1, Sonnet | 43 of 55 (78%) | 57 of 76 (75%) | 9 of 1,294 (0.7%) |
| C2, Haiku | 34 of 55 (62%) | 38 of 76 (50%) | 16 of 1,294 (1.2%) |

**Every one of 192 new mentions was a verbatim quote, in the right turn, by the right speaker.** A session reading a whole conversation produced a usable ledger in about 90 seconds, and it needed no correction to be valid. Whether it's *right* is what this test can't say.

## Disagreements and integrity
**What reproduced across all ledgers, blind:**
| Question | A | B | C1 | C2 |
|---|---|---|---|---|
| Central project's contradiction reported | yes | yes | yes | yes |
| Business kept apart from the personal practice | yes | yes | yes | yes |
| "Was it one thing or two?" raised for the two similar businesses | yes | yes | yes | yes |
| "Accepted" not treated as "started" | yes | yes | yes | yes |
| Ended jobs marked ended | yes | yes | yes | yes |
| Whether two similarly named placements are the same, raised | yes | yes | yes | yes |

**What didn't:**
| Case | Disagreement |
|---|---|
| **My 8E split of one project into "building" and "operating"** | no other reader did it. All kept one activity and flagged it contradictory. **My split was a choice, not a finding** |
| **Two similar businesses** | B merged them; C1 and C2 kept them apart. **All flagged it.** The merge is visible |
| **Sub-activities** | some readers keep a sub-task inside the project; others make it separate |
| **Entering versus hosting** | B and A kept both, and raised it. C1 and C2 omitted both |
| **Past habit, then a recent event** | C1 flagged it; C2 merged them unflagged. **This is the one quiet merge of real concern** |

**8E's worry was wrong.** I said separating the contradiction needed hindsight no extractor would have. In fact whole-conversation agents found it unaided. The hindsight objection only applies to per-message extraction.

**The invented continuity** is one case, the same activity in all three: last evidence one session before the end, called still engaged. C1 itself raised it for review. It's a real breach of the rule, and it's mild.

**The uncertainty is more reproducible than the structure.** Readers disagree on boundaries, yet they raised largely the same questions for review.

## Post-hoc analyses
**Ideas formed after seeing results, and outside the frozen decision.**
| Idea | Result | |
|---|---|---|
| **Let the classifier compute final state, ignoring the reader's** *(withdrawn: Phase 8G found this agreement mostly mechanical, not correct)* | state kappa, A with C1, rises from 0.24 to 0.81; A with C2, from 0.45 to 0.53. Invented continuity is 0 by construction | **strong** |
| **Only compare activities of 3 or more mentions** | A with B stays at adjusted Rand 0.52 | **refuted**: granularity isn't confined to small activities |

## Temporal contradictions
See the [design](temporal-contradiction-design.md). **The main finding overturned my draft:** the code check I proposed in 8E reports nothing on the new ledgers, because no reader used the `negated` role. Reading found them; code comparing states didn't.

## Recommendation: simplify
**Don't implement the activity and engagement model as proposed.** Criteria 1, 2 and 5 aren't met, and the rule says so. **Don't abandon the idea either.** Provenance, contradiction reporting and final-state agreement were all strong, and what failed is specific.

**What the evidence supports is a smaller thing: a review-first activity index.**
| Keep | Drop |
|---|---|
| whole-conversation consolidation, not per-message | per-mention certainty levels: not reproducible |
| coarse groups as **proposals, never accepted automatically** | any claim of a "right" granularity |
| verbatim quote validation: it held at 100% | sub-activity structure |
| contradictions and review items as first-class output | model-written final states |
| final state computed by the classifier, always | the `engagement` schema, for now |

**Next steps, all free:**
1. **Replicate on the second development conversation.** One conversation can't support any of this.
2. **A human reader,** on at least one conversation. Every ledger here is Claude's. This is the largest remaining gap.
3. **The independent answer pack** decides whether any of this improves answers.

**No schema until those three are done.** Nothing here shows activity memory improves an answer.

## Limits
- One conversation, already used in 8A to 8E. It has a strong central storyline, which may flatter agreement.
- All ledgers are from one vendor's models, sharing training and possibly the same blind spots.
- Thresholds were my judgement, set before the results, not established standards.
- The contradiction classification is mine and unverified.
- Ledger A had access to the scheme it was then compared with.
