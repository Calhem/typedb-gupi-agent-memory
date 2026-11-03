# Specialist direction: documents for review

Owner direction (2026-11-03): GUPI becomes a specialist memory engine for agents working with complex,
evolving and potentially contradictory knowledge. Whether TypeDB's typed relationships, temporal reasoning,
provenance and constraints give more reliable knowledge management is **a hypothesis to test**.

| Document | Contents |
|---|---|
| [v2-truth-semantics.md](v2-truth-semantics.md) | **Directions approved, not implemented:** v2 semantics (evidence first, FALSE only with negative evidence, negations independent of terminations, overlap judged by compatibility and coverage, a basis on every result); truth table R1-R23 as proposed acceptance tests (`tests/acceptance/`); decisions Q1-Q8, open Q9; ADR proposal in ../adr/0009 |
| [authoring-trial/](authoring-trial/README.md) | **Approved, not started:** two-document authoring trial before the mini-pilot; logs for authoring time, disagreements and representational limitations (CSV templates) |
| [authoring-trial/guidelines-v0.md](authoring-trial/guidelines-v0.md) | **Draft v0 (revision 2), approved for external review:** implementation-neutral annotation guidelines (source statements vs annotator judgements, three times, attribution, negation/termination/reinstatement, answer statuses and evidence sets, adjudication, JSON Lines format), with worked examples, recorded-knowledge vs actual-condition questions, and evidence standing (revision 2); spreadsheet template in [annotation-template/](authoring-trial/annotation-template/README.md); bias audit in [bias-audit-v0.md](authoring-trial/bias-audit-v0.md) |
| [authoring-trial/scoring-protocol-v0.md](authoring-trial/scoring-protocol-v0.md) | **Draft, primary:** a common structured answer contract for all systems (answer, uncertainty, evidence, explanation), scored deterministically with all essential evidence needed for full credit; explanations and evidence support audited separately by people |
| [authoring-trial/scoring-nl-experimental-v0.md](authoring-trial/scoring-nl-experimental-v0.md) | **Experimental secondary metric, potentially brittle:** word-list scoring of free-text answers |
| [authoring-trial/reviewer-package/](authoring-trial/reviewer-package/README.md) | **Ready for an independent reviewer:** short introduction, practice passages without answers, a 13-question form, and a SHA-256 manifest of the files reviewed |
| [authoring-trial/system-mappings-v0.md](authoring-trial/system-mappings-v0.md) | Provisional, reformat-only mappings from each system's output to the answer contract; frozen before any held-out run |
| [authoring-trial/trial-report-template.md](authoring-trial/trial-report-template.md) | What the trial report captures: conclusion and evidence-supported accuracy, unmatched answers, contract failures, disagreements, auditor agreement, time |
| [authoring-trial/dry-check/](authoring-trial/dry-check/README.md) | Dry check of the template on the guidelines' examples: complete, lossless export (tested) |
| [authoring-trial/review-checklist-v0.md](authoring-trial/review-checklist-v0.md) | Checklist for an independent reviewer unfamiliar with GUPI: neutrality, consistency, ambiguous examples, missing phenomena, scoring |
| [authoring-estimate.md](authoring-estimate.md) | Effort for the trial (4.5-7.5 h + 2.5-4 h), the 8-document mini-pilot (14-22 h + 2-3 h) and the held-out split (37-57 h + 5-7 h) |
| [m1-protocol.md](m1-protocol.md) | **For approval:** the M1 methodology pilot (not a competitive benchmark): five hypotheses H1-H5 attributed to application logic, modelling or TypeDB; baselines; error injection; ~40 documents and ~80 questions; authoring and bias controls; stop conditions |
| [joined-spell-analysis.md](joined-spell-analysis.md) | **For approval:** joined-spell behaviour vs ADR 0007 on five scenario types; four defects (D1-D4); proposed v2 semantics (TRUE / PRESUMED / UNKNOWN / FALSE / CONTESTED, spells first), versioned |
| [review.md](review.md) | **Critical review of all of the below** (2026-11-03): where TypeDB does and does not provide an advantage, failure modes, a fair evaluation matrix, staged milestones, decisions needed. Where it disagrees with the documents below, the review's recommendations apply. |
| [benchmark-assessment.md](benchmark-assessment.md) | CronQuestions, AVeriTeC, ComplexWebQuestions, LongMemEval: licence, protocol, capabilities, fit, LLM/search needs, complexity; recommends two |
| [memory-formation-engine.md](memory-formation-engine.md) | Proposed formation pipeline; salience, support and acceptance as separate decisions |
| [domain-and-evaluation.md](domain-and-evaluation.md) | `projects` domain model, chronological dataset design, question families, baselines, metrics |
| [capabilities.md](capabilities.md) | Existing vs proposed capabilities vs unproven hypotheses |
| [roadmap.md](roadmap.md) | Revised phases and the decisions needed |

The month-without-year date bug is fixed in `main` (PR #1, merge commit `d360ff3`).
Nothing in these documents is implemented, and no new dataset has been downloaded. The next step is the
owner's review.
