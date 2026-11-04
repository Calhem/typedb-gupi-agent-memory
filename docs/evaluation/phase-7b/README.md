# Phase 7B: model-assisted extraction experiment (Stage 1: design)

**The objective:** decide whether model-assisted extraction materially improves GUPI's ability to form
reliable memories from unfamiliar evidence. It is tested on two things together:
- **Coverage:** more relevant facts than `rules:v2.1`.
- **Evidence integrity:** attribution, time, certainty, polarity, provenance and corrections, all preserved.

**Recall bought with unsupported or misleading claims is a failure.**

## Status
**Stage 1 (design) is complete.** **Stage 2 is blocked**, waiting on two things:
1. **Independent contributors:** the corpus authors, the annotators and an adjudicator.
2. **The owner's approvals:** see stage-2-plan.md.

**None of the following has happened:**
- no extractor implemented
- no model called
- no model downloaded
- no corpus written

**Spending:** the lifetime API spend is $0, and the authorised spend is $0.

**The manifest:** it is a **draft** (manifest.draft.json) and must not be used to report results.

Branch `feature/phase-7b-extraction-design`, from main `0d3ca00`. It is not merged.

## Stage 2A (branch `feature/phase-7b-offline-harness`, not merged)
| File | Contents |
|---|---|
| [stage-2a-results.md](stage-2a-results.md) | the summary, tests, before and after, reproduction |
| [contract-corrections.md](contract-corrections.md) | C1 fixed; D3 enforced (one extension awaiting approval); organisational-claimant diagnosis (extension awaiting approval) |
| [offline-extractor-interface.md](offline-extractor-interface.md) | `model:candidate-v1` and the `gupi.model-response/1` format (offline; no model connected) |
| [offline-harness.md](offline-harness.md) | the harness that scores rules:v2.1 against recorded model outputs |
| [development-fixtures.md](development-fixtures.md) | the developer-authored engineering fixtures (not evidence) |
| [remaining-limitations.md](remaining-limitations.md) | the decisions awaiting approval, findings (F1), limits, and the blockers before a live evaluation |

## Documents
| File | Contents |
|---|---|
| [evaluation-protocol.md](evaluation-protocol.md) | questions Q1–Q5, the systems compared, the order of work, blinding |
| [corpus-specification.md](corpus-specification.md) | S1 (specialist, about 40 passages, primary) and S2 (conversational, about 40 turns, secondary); independence rules |
| [annotation-guidelines.md](annotation-guidelines.md) | the gold annotation contract, ambiguity handling, adjudication |
| [annotation-templates/](annotation-templates/README.md) | blank CSV templates and the contributor declaration; checker `gupi.benchmarks.phase7b.annotations` |
| [candidate-contract-audit.md](candidate-contract-audit.md) | `gupi.candidate/1` field by field; findings C1–C8 |
| [model-extractor-design.md](model-extractor-design.md) | `model:candidate-v1` (design identifier only): output schema, grounding, outcomes |
| [scoring-specification.md](scoring-specification.md) | matching tiers, metrics, special cases; no LLM judge |
| [success-criteria.md](success-criteria.md) | thresholds T1–T10, hard failures H1–H3, the stopping rule, statistical limits |
| [model-options.md](model-options.md) | verified prices; the work on the Claude extractor; cost and latency estimates; local models |
| [reproducibility-plan.md](reproducibility-plan.md), [manifest.draft.json](manifest.draft.json) | what is frozen, when, and by whom |
| [stage-2-plan.md](stage-2-plan.md) | approvals G1–G7, decision D3, sequence |

**About the examples:** the passages and JSON shown in these documents are developer-authored
illustrations. They are not evaluation material.

## Stage 1 findings
1. **Does the existing contract support the proposed extractor?**
   - **Mostly yes.** `gupi.candidate/1` already carries the passage, participants, time kinds, polarity,
     modality, commitment, attribution (claimant, mode, intermediaries, transmission) and relations.
   - **Code can check it:** every offset and window can be computed and checked deterministically.
   - **Three preconditions:**
     - **C1:** schema-aware validation rejects every generic `statement`. A strict expected-failure test
       demonstrates it.
     - **The schema:** the store path must be called with the live schema.
     - **D3:** a decision on unresolved correction targets.
2. **Representational limits that the scoring must treat as gaps,** not as model errors:
   - allegations or disputes as such (C4)
   - typed ownership, control or investigation (C5: `statement` only)
   - identity ambiguity (C6)
   - approximate times (C7: kept as phrases, sent to review)
   - organisational claimants stored as people (C2)
3. **The defaults are dangerous (C8):** they are certain, direct, actual and positive. The model must state
   every one of these fields, or the output is invalid.
