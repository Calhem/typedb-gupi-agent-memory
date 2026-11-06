# GUPI Phase 8A: relationship-aware retrieval proposal

**Status (2026-11-06): proposal for review. Nothing is implemented.** Branch
`feature/phase-8a-relationship-retrieval-design`, from `main` `6db22d4`. No production code changed, no paid API call,
no model download, no held-out data used. Not merged.

## Executive summary
**What is the smallest change to GUPI that could demonstrate a meaningful TypeDB contribution to agent memory
retrieval?**

**Add one small module, about 300 lines with no schema change, that starts from keyword hits and follows TypeDB
relationships in two layers: who said it and what was said next to it, then one or two hops through believed claims,
returning each path with its evidence and qualifications. Then test the second layer on a new, frozen question set
where claims exist.**

**What the investigation found:**
1. **The 0.000 structured score does not test TypeDB.** LoCoMo produced no claims, so there was no graph, and the
   retriever had no relevance signal. It says nothing either way about relationships.
2. **Connecting claims is where TypeDB is underused.** Text retrieval and claims are never joined today. Python's
   temporal logic, by contrast, is in the right place and should stay there.
3. **Relationships already stored help real chat.** On LoCoMo development data, keyword plus authorship and
   neighbouring turns, with no extraction, moved multi-hop recall@10 from 0.195 to 0.301, and recall@10 overall from
   0.587 to 0.693. Traversal cost is small: under 70 ms on 2,649 claims with a large hub.
4. **That gain is not yet a TypeDB advantage,** and it misses the 15-point target at this stage: +10.6 at recall@10
   and +5.5 at recall@5, from 42 questions, after eight variants. Adversarial recall@5 falls 4.3 points. Authorship and
   turn order would work in any store.
5. **The real test is claim paths with time and provenance,** which text cannot do. All eight proposed queries ran on
   TypeDB 3.14.1, and on the Alice scenario time stayed honest: PRESUMED in 2022, UNKNOWN in 2023, FALSE in 2024.
6. **Extraction on chat is the biggest risk.** Without claims there are no paths on conversations. That needs a
   decision before any leaderboard work.

**Recommendation:** approve 8B on the terms in part 5. If claim paths do not beat structure alone by 10 points on the
frozen set, TypeDB's relationship contribution has not been shown, and we diagnose before adding anything.

**Ideas dropped on evidence:** linking turns by named entities (no gain), text-only query expansion (worse), and
filtering by speaker (halves adversarial recall).

## Contents
| Part | Covers | Brief items |
|---|---|---|
| [01-current-architecture.md](01-current-architecture.md) | the system map, stored relationships, why structured retrieval failed, where evidence is lost | 1, 2 |
| [02-retrieval-design.md](02-retrieval-design.md) | design, TypeDB and Python responsibilities, tested queries, identity, ranking, budgets | 3, 4, 6 |
| [03-schema-and-temporal.md](03-schema-and-temporal.md) | schema impact, temporal preservation, the one-time event limitation | 5 |
| [04-evaluation-protocol.md](04-evaluation-protocol.md) | feasibility results, datasets, systems, metrics, stop conditions | 7 |
| [05-milestones-and-costs.md](05-milestones-and-costs.md) | 8B–8E, what to remove, costs, risks, decisions needed | 8, 9, 10 |
| [probes/](probes/) | the measurements behind every number | – |

**How to read the numbers:** everything here is development data or synthetic, and is an estimate, not a benchmark
score. LoCoMo results stay out of external claims until its licence question is resolved (`docs/known-issues.md`).
