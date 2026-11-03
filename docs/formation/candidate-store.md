# The candidate store (core/0012)

Date: 2026-11-03.
- **Code:** `gupi.formation.store`.
- **Tests:** `tests/integration/test_candidate_store.py`, against TypeDB 3.14.1.
- **Decision:** option C of candidate-persistence.md, approved.

## Schema (`core/0012_candidate_store.schema.tql`)
It is additive only, applied after `core/0011`.

| Type | Holds | Why typed |
|---|---|---|
| `memory-candidate` | `gupi-id @key` (the candidate id), `ir-version`, `candidate-payload` (the exact canonical gupi.candidate JSON), `method` (extractor), `recorded-at`, `proposition-key` (of the claim it would become) | identity and lookup |
| `candidate-of` | candidate ↔ observation, with `span-start` and `span-end` (the exact passage) | the source link must be integrity-checked |
| `formation-decision` | `decided` (the candidate): `gupi-id @key`, `formation-outcome` (`formed`, `withheld`, `review`, `rejected`), `decided-by`, `reason`, `recorded-at` | an append-only history that can be queried |
| `formed-into` | candidate ↔ the claim formed from it | lifecycle link |
| `correction-suggestion` | `suggested-by` (candidate), zero or more `target` claims: `gupi-id @key`, `target-resolution` (`resolved`, `missing`, `ambiguous`), `reason`, `recorded-at` | targets must be real claims |

**Kept as JSON, not as attributes:** the candidate's content. That includes participants, time readings with
phrases, windows, precision and assumptions, modality, commitment, polarity, attribution and transmission,
and relations. It is stored as one canonical JSON payload, the validated `gupi.candidate/1` record. It is
not split into attributes, so it survives changes to extraction logic exactly as it was extracted.

## Lifecycle
1. **`submit(memory, observation, cset)`.**
   - Validates the set, and stores each valid candidate with the policy's (`formation:v1`) first decision.
   - Structurally invalid candidates are **not stored**; they are listed in the result.
2. **The first decision** is one of:
   - `formed`: the claim, its acceptance review, the decision and `formed-into` are written in **one
     transaction**
   - `withheld`: plans, hypotheticals, forwarded copies, inexpressible times
   - `review`: hedges, rumours, corrections, unreadable stated times
3. **`pending(memory, at=None)`** lists candidates whose latest decision, as of `at`, is `review`.
4. **`get(memory, id)`** returns the stored candidate (exact payload), its observation, its decision
   history, its formed claim and its suggestions.
5. **`review(memory, id, "approve" | "reject", reviewer, reason)`** appends a decision.
   - **Approval** forms the claim only where the policy allows. A plan stays `withheld`, with "approval
     cannot form it". A hedge keeps its commitment on the claim, and its answers stay qualified (not
     definitive). Formation is atomic, as above.
   - **Rejection** keeps the candidate, marked `rejected`.

## Review semantics
- **Append-only.**
  - Every decision is a new `formation-decision`, and none is ever altered or deleted.
  - The latest decision is the current status. `status_at(t)` gives the status at any earlier time.
  - Earlier decisions stay readable.
- **Order is unambiguous.**
  - A decision must be recorded strictly after the previous one.
  - A stalled clock is refused (`ValueError`) rather than allowed to make the order depend on ids.
- **No override by re-runs.** Submitting the same candidates again records nothing. The policy's decision is
  recorded only on first submission, so a re-run never overrides a reviewer. Repeating the latest decision
  (same outcome, decider and reason) records nothing.
- **A formed candidate takes no further candidate decisions.** Retracting what it became is a claim review
  (`Memory.review(claim, "retracted", ...)`), which keeps the claim's own history.
- **Corrections are never applied.**
  - A stated correction stores a suggestion naming its target claims:
    - `resolved`: one target
    - `missing`: none in memory
    - `ambiguous`: several, none chosen
  - A supersession is still recorded only by `Memory.supersede`.
- **Acceptance is not verification.** A formed claim is admitted into memory, with its decider recorded. Its
  v2 answers carry the evidential qualification (6c-hardening.md).

## Under belief-time (as-of) queries
- **Candidates and decisions never affect answers,** at any belief time: they are not claims.
- **A formed claim is recorded at its formation decision's time.** As-of queries before that do not see it.
  Its acceptance review has the same time.
- **`pending(at)` and `status_at(at)`** reconstruct the review state as it was at `at`: only candidates and
  decisions recorded by then count.

## Integrity checks
- **Exact text:** the payload is the canonical JSON (sorted keys, no extra whitespace) and round-trips
  exactly. On every read, the candidate id is recomputed from the payload, and a mismatch (an altered
  payload) is refused.
- **Exact source:** the observation is rebuilt from TypeDB for review, and its id must come out the same.
- **No merging:** referents are scoped to the conversation, as in formation; names are never merged.
- **Originating speakers and transmission** are kept in the payload, and on formed claims (core/0011).

## Migration compatibility
- **Order:** `0012` is applied after `0011`.
- **Existing data:** a populated `0011` database migrates with every claim, id and proposition key
  unchanged (tested).
- **Behaviour:** v1 remains the default. v2's temporal and evidential behaviour is unchanged.
- **Phase 4:** the results are unchanged.
- **Rollback:** restore the pre-migration export (ADR 0004).

## Remaining integrity risks
| # | Risk | Note |
|---|---|---|
| S1 | Structurally invalid candidates are not stored | only reported by `submit`. What an extractor got wrong is not kept durably. |
| S2 | Suggestions are computed when a decision is recorded | a claim added later is not reflected until the candidate is decided again |
| S3 | Correction targets are found by proposition key within one conversation | corrections across conversations are `missing` |
| S4 | `pending` reads every stored candidate | linear in the store's size; fine for a prototype |
| S5 | A formed candidate's status stays `formed` | even if its claim is later retracted; the claim's reviews carry that |
| S6 | Two formation paths exist | `form()` (no store) and the store. Using both on the same candidates writes the same claim (idempotent), but only the store records decisions durably. Use one per deployment. |
| S7 | Reviewer identity is a plain string | there is no authentication |
| S8 | The same name in one conversation is one referent | audit H9, deferred |
