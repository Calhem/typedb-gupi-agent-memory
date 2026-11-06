# Phase 8F protocol

**Fixed before any reader ran:** this file, [the annotation manual](annotation-manual.md), [the consolidation specification](consolidation-spec.md), `benchmarks/phase8f.json` and `phase8f_agreement.py`.

## Who produces what
**No human annotator is involved anywhere in this phase.** Every ledger comes from a Claude model, under the same subscription, from the same vendor. Separate agents have separate contexts. That is not human independence.

| Ledger | Producer | Instructions | Prior exposure |
|---|---|---|---|
| A, first reader | Claude Opus 5.5, the session that built GUPI | Phase 8E, converted to the common format and hashed before the others ran | had seen this conversation, and designed the scheme |
| B, second reader | a fresh Claude Sonnet agent with no conversation history | annotation manual | none |
| C1, automated | a fresh Claude Sonnet agent | consolidation specification | none |
| C2, automated | a fresh Claude Haiku agent, the nearest available stand-in for a low-cost model | consolidation specification | none |

**Blindness.** Each agent gets its own folder holding only the conversation and its instructions. It doesn't receive the ledger, decisions, schema, counts, conclusions, questions or gold, and is told to open nothing else. This is checked afterwards from its tool calls. Any access outside its folder invalidates that run.

**A known limit:** I wrote the annotation scheme, so its roles and vocabulary are shared by every reader. That raises agreement. It's not a measure of agreement on what the categories should be.

## Measures
Readers label and bound activities differently, so ids are ignored.
| Question | Measure |
|---|---|
| Do they find the same mentions? | matched by overlapping quotes in a turn; F1 |
| Do they find the same activities? | one-to-one alignment on shared mentions, Dice at least 0.5; F1 |
| Do they group mentions alike? | adjusted Rand index (chance-corrected) and B-cubed F1, over matched mentions |
| Same role? | Cohen's kappa, on five role groups |
| Same explicit or uncertain link? | Cohen's kappa |
| Same temporal state? | kappa on final state, over aligned activities |
| Contradictions | shared by turn overlap |
| Merges and splits | activities taking at least two mentions from each of two activities in the other ledger. **Disagreement, not error** |
| Invented continuity | `engaged` at the end, with no mention in the last session |
| Provenance | every quote checked word for word in its turn and against its speaker |

**The reference standard.** There is no defensible gold. Precision against one reader would just crown that reader. Automated output is scored only against **what A and B agree on**, as a floor; everything else stays undecided and goes to the disagreement list. No disagreement is resolved in favour of the first ledger.

## Decision thresholds
From `benchmarks/phase8f.json`. A criterion passes only if all its measures do.
| Criterion | Pass |
|---|---|
| 1. Reproducible boundaries and links | A with B: mention F1 at least 0.70, activity F1 at least 0.60, adjusted Rand at least 0.70, B-cubed F1 at least 0.75 |
| 2. False merges and invented continuity rare and identifiable | merge rate at most 0.15; no invented continuity |
| 3. Provenance complete | at least 98% of mentions valid before removal, and 100% after |
| 4. Temporal ambiguity explicit | final-state kappa at least 0.60, and the known kind of conflict is reported by each ledger |
| 5. Automation feasible | at least one automated ledger reaches mention F1 and adjusted Rand thresholds against A and B, and correction share at most 0.30 |

Roles at kappa 0.60 and links at kappa 0.40 are reported as supporting measures.
