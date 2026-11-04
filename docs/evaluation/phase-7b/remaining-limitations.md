# Remaining limitations and blockers (after Stage 2A)

## Decisions waiting for approval (stopped in Stage 2A, as required)
| Id | What | Proposal | Effect until decided |
|---|---|---|---|
| **C2** | organisational and unknown-kind claimants are stored as people | `gupi.candidate/1.1` adds an optional `Attribution.asserted_by_kind`; persistence uses it; absent means person for version 1 and unclassified for version 1.1 (contract-corrections.md) | `model:candidate-v1` refuses non-person claimants (`claimant-kind-not-representable`): lost recall, no false person; rules:v2.x unchanged |
| **D3 extension** | a correction with no resolvable target and no leading cue cannot be routed to review | `gupi.candidate/1.1` allows `target = null` for corrects, retracts and updates; formation always reviews it | `model:candidate-v1` produces no candidate (`correction-target-unresolved`) |
| **Inferred basis** | formation:v1 forms an `inferred` candidate without review | either route `basis = inferred` to review (a formation policy change), or keep deferring inferred statements until their evidence can be represented safely. **Inferred statements are never admitted automatically** | `model:candidate-v1` refuses inferred assertions (`inferred-not-admissible`) |

## Findings recorded, not fixed
| Id | Finding | Evidence | Proposed regression test |
|---|---|---|---|
| **F1** | A second forwarded copy of a statement that itself arrived forwarded is **formed**, not withheld. `_existing_copies` only withholds copies of a first-hand claim. Answers still count one originator, because the qualification counts distinct originators, but memory holds two claims for one attestation. | DEV-107 and DEV-108, for both rules:v2.1 and model:candidate-v1 (`copies_formed = 1`) | two forwarded copies of the same statement with the same header sender, in different messages: the second is withheld as a copy |
| C4 | allegations and investigations have no contract field: they are kept as statements with reported or rumour mode, and flagged `allegation` | DEV-105, DEV-123 | — (an ontology decision) |
| C6 | identity ambiguity ("Dana from finance") has no field | DEV-117 | — |
| C7 | approximate dates ("around 2019") are unread, so they are kept as phrases with precision unknown and reviewed | DEV-118 | — |

## Limits of the offline interface (by design, or heuristic)
- **The cue checks are word lists:**
  - **What they are:** hedges, negations, future and conditional words, read from the sentence start.
  - **Their failure modes:** they can raise false conflicts (a negation in an unrelated clause), and can miss
    an unlisted hedge.
  - **How they fail:** on the safe side. Either no candidate, or commitment `unknown` so that formation
    reviews it.
- **The present-tense reading** of `holds-at` verbs is the rules:v2 heuristic (a fixed verb list).
- **Correction targets** match only on identical participant surfaces and type. A correction that names a
  person differently ("Omar" against "Omar Siddiq") is unresolved, which is safe but loses recall.
- **No coreference, by design:** pronoun-carried facts are refused, never resolved.

## Limits of the Phase 6D comparison tool
- **What it misses:** `gupi.benchmarks.e2e.compare` does not ignore the scale probe's per-observation timing
  fields (`*_s_per_obs`). Reruns therefore show them as differences, although they are timings.
- **Why it is not fixed now:** manifest version 2 records the tool's hash, so fixing it means a version 3.
- **Where this is stated:** docs/evaluation/phase-6d/REPRODUCTION.md.

## Limits of the harness
- **Surface matching:**
  - **The rule:** exact matching is on normalised surfaces and predicates, so paraphrased statement predicates
    become partial matches.
  - **What happens to them:** they go to human adjudication. The adjudication step itself, recording decisions
    and re-scoring, is specified but not yet a tool.
- **The time comparison:**
  - **What is checked:** the window of the first time of the gold kind.
  - **What is not:** several times of the same kind.
- **Formation order:** passages with the same date are ordered by thread, then passage id. Real arrival order
  is not modelled.
- **Representable recall** excludes gold marked `gupi_claim_type = none`. Their abstention is counted
  separately.

## Blockers before any live model evaluation
1. **G1:** independent authors, two annotators and an adjudicator, and the frozen S1 and S2 corpus and gold.
   Nothing here substitutes for them.
2. **The contract decisions:** C2, the D3 extension and the inferred-basis policy above. Each is optional for
   running, but without them the model's recall on attributed, corrected and inferred statements is capped.
3. **G4:** approval to connect `model:candidate-v1` to a live model, with a prompt that emits
   `gupi.model-response/1` and a recorder for its responses.
4. **G5 and G6:** an API key for an account with credits (a Claude Max subscription does not provide them),
   and spending approval. **The authorised spend today is $0.**
5. **Freezing:** freeze the prompt, scorer and thresholds, and finalise the manifest (still a draft), before
   the first scored run.
