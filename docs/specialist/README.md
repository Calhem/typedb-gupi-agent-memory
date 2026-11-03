# Specialist direction: documents for review

Owner direction (2026-11-03): GUPI becomes a specialist memory engine for agents working with complex,
evolving and potentially contradictory knowledge. Whether TypeDB's typed relationships, temporal reasoning,
provenance and constraints give more reliable knowledge management is **a hypothesis to test**.

| Document | Contents |
|---|---|
| [m1-protocol.md](m1-protocol.md) | **For final approval:** the M1 methodology pilot: five hypotheses (method vs TypeDB), metrics, stop conditions, dataset-generation protocol |
| [joined-spell-analysis.md](joined-spell-analysis.md) | **For approval:** joined-spell behaviour vs ADR 0007, a second spell defect found, and a versioned proposal (PRESUMED outcome, spells first) |
| [review.md](review.md) | **Critical review of all of the below** (2026-11-03): where TypeDB does and does not provide an advantage, failure modes, a fair evaluation matrix, staged milestones, decisions needed. Where it disagrees with the documents below, the review's recommendations apply. |
| [benchmark-assessment.md](benchmark-assessment.md) | CronQuestions, AVeriTeC, ComplexWebQuestions, LongMemEval: licence, protocol, capabilities, fit, LLM/search needs, complexity; recommends two |
| [memory-formation-engine.md](memory-formation-engine.md) | Proposed formation pipeline; salience, support and acceptance as separate decisions |
| [domain-and-evaluation.md](domain-and-evaluation.md) | `projects` domain model, chronological dataset design, question families, baselines, metrics |
| [capabilities.md](capabilities.md) | Existing vs proposed capabilities vs unproven hypotheses |
| [roadmap.md](roadmap.md) | Revised phases and the decisions needed |

The month-without-year date bug is fixed separately on branch `fix/month-without-year` (unmerged).
Nothing in these documents is implemented, and no new dataset has been downloaded. The next step is the
owner's review.
