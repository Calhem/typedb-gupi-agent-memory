# Specialist direction: documents for review

Owner direction (2026-11-03): GUPI becomes a specialist memory engine for agents working with complex,
evolving and potentially contradictory knowledge. Whether TypeDB's typed relationships, temporal reasoning,
provenance and constraints give more reliable knowledge management is **a hypothesis to test**.

| Document | Contents |
|---|---|
| [v2-truth-semantics.md](v2-truth-semantics.md) | **For approval:** revised v2 semantics (evidence first, FALSE only with negative evidence), truth table R1-R15 for D1-D4 with valid- and belief-time boundaries, open questions Q1-Q8; ADR proposal in ../adr/0009 |
| [authoring-estimate.md](authoring-estimate.md) | Effort for the held-out split (37-57 h + 5-7 h) and an 8-document mini-pilot (14-22 h + 2-3 h) |
| [m1-protocol.md](m1-protocol.md) | **For approval:** the M1 methodology pilot (not a competitive benchmark): five hypotheses H1-H5 attributed to application logic, modelling or TypeDB; baselines; error injection; ~40 documents and ~80 questions; authoring and bias controls; stop conditions |
| [joined-spell-analysis.md](joined-spell-analysis.md) | **For approval:** joined-spell behaviour vs ADR 0007 on five scenario types; four defects (D1-D4); proposed v2 semantics (TRUE / PRESUMED / UNKNOWN / FALSE / CONTESTED, spells first), versioned |
| [review.md](review.md) | **Critical review of all of the below** (2026-11-03): where TypeDB does and does not provide an advantage, failure modes, a fair evaluation matrix, staged milestones, decisions needed. Where it disagrees with the documents below, the review's recommendations apply. |
| [benchmark-assessment.md](benchmark-assessment.md) | CronQuestions, AVeriTeC, ComplexWebQuestions, LongMemEval: licence, protocol, capabilities, fit, LLM/search needs, complexity; recommends two |
| [memory-formation-engine.md](memory-formation-engine.md) | Proposed formation pipeline; salience, support and acceptance as separate decisions |
| [domain-and-evaluation.md](domain-and-evaluation.md) | `projects` domain model, chronological dataset design, question families, baselines, metrics |
| [capabilities.md](capabilities.md) | Existing vs proposed capabilities vs unproven hypotheses |
| [roadmap.md](roadmap.md) | Revised phases and the decisions needed |

The month-without-year date bug is fixed separately on branch `fix/month-without-year` (unmerged into `main`;
merged into this branch).
Nothing in these documents is implemented, and no new dataset has been downloaded. The next step is the
owner's review.
