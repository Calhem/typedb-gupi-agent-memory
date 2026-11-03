# Formation pathway (Phase 6C): validated candidate → decision → accepted claim

Date: 2026-11-03.
- **Code:** `gupi.formation.form`.
- **End-to-end tests:** `tests/integration/test_formation.py`, against TypeDB 3.14.1.
- **Schema:** core/0011. core/0012 (candidate storage) is not implemented.

## What formation means
- **Formation records that an assertion was accepted into memory.** It does not record that the assertion
  is true.
- **A formed claim is recorded,** and then accepted by an explicit review. The decider is either the policy,
  `formation:v1`, or the named reviewer who approved it. It is believed from that moment of transaction time
  onwards.
- **Earlier belief times are unchanged:** asking "as of" before then gives the same answers as before.

## The policy (`formation:v1`)
Each candidate gets exactly one decision:

| Candidate | Decision | Why |
|---|---|---|
| rejected by a named reviewer | **rejected** (decided by that reviewer) | a recorded refusal |
| fails structural or schema validation | **rejected** | no claim from malformed or unsupported input |
| modality other than `actual` (planned, hypothetical, ...) | **withheld** | a plan is never answered as a fact |
| repeats another candidate in the same observation, or a claim already in memory, as a forwarded or quoted copy (same type, polarity and words; in any conversation) | **withheld** | not an independent attestation |
| time that a valid time cannot express ("was CTO in March") | **withheld** | no invented bounds |
| hedged (`probable`, `possible`, `unknown`), rumour, or a stated correction, with no reviewer approval. This includes a passage that opens with a correction cue whose target the extractor could not name, and a stated time that could not be read. | **review** | needs an explicit decision |
| the same, approved by a named reviewer | **formed**, accepted by that reviewer | the uncertainty is kept on the claim (`commitment`) |
| otherwise: an asserted actual condition or event | **formed**, accepted by the policy | |

A candidate that cannot be formed without inventing something is **rejected**, for example first person with
no known author.

## What a formed claim keeps
| What | Where |
|---|---|
| source passage | evidence: observation and the passage span; mentions for each participant |
| participants | referents scoped to the conversation or document (as in the existing contract). Identical names elsewhere are **not** merged; merging stays an explicit identity decision. |
| who asserted it and how | `assertion` (the asserter referent) and `attribution-mode` |
| the source's certainty | `commitment` |
| temporal basis | valid-time bounds from the candidate (candidate-ir.md §5), with `valid-from-basis` `stated` or `lower-bound`. "Since March" never becomes an exact start. |
| polarity | `polarity` (negations) |
| provenance | `method` (the extractor), `candidate-id`, the acceptance review, and the formation run (an `extraction-run` with method `formation:v1`, whose report lists **every** decision, including rejected, withheld and review ones) |

## Corrections
A stated correction is routed to review. Its decision carries a suggestion, even while it awaits review:
- **The target** is the claim its named target became. Failing that, the suggestion lists every believed
  claim about the same proposition in the same conversation.
- **Ambiguity:** more than one possible target is flagged as ambiguous, and none is chosen.

Once approved:
- its own claim is formed
- the decision carries a **suggestion**: the claim its target became (old), and the new claim

**Nothing is superseded.** Both claims stay believed until a reviewer records a supersession with
`Memory.supersede`.

## Idempotency
- **Ids:** candidate, claim and run ids come from their content.
- **Repeating a formation** writes nothing new. Ingestion skips existing records, a repeated identical review
  is a no-op, and an existing run is not recorded again.

## Limits
- **Answers do not yet use the new fields.** v1 and v2 answer a hedged or reported claim as they would a
  certain, direct one. The commitment and attribution are stored and can be cited, but are not weighed.
- **Candidates are not stored** (core/0012). A withheld or review candidate exists only in the run report's
  decision list. To approve one later, re-run its extraction (which is deterministic) and pass the approval.
- **The asserter is created as a person** scoped to the observation, like any participant.
