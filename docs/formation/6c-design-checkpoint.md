# Phase 6C design checkpoint: the minimum needed to form candidates into claims

Date: 2026-11-03. Status: **design only, for the owner's schema decision.**
- **No candidate persistence and no formation code exist.**
- **`core/0011` is still not applied.**

This document narrows the earlier proposal (integrity-and-schema.md §3) using what 6B showed.

## 1. What 6B showed that matters for the schema
- **Lower-bound continuity is common, and needs keeping.** Six of the 31 expected candidates in the frozen
  set are `holds-since`. Their bounds alone (no earliest start, a latest start) already answer correctly
  under v2. But without a basis attribute, a stored claim cannot say *why* its start is open: whether "since"
  was said, or the start is simply unknown.
- **Attribution changes meaning.** Without the mode, these all become the author's own assertion:
  - reported speech ("X told me that ...")
  - forwarded copies
  - rumours

  A forwarded copy that `repeats` an original must not count as independent corroboration. Today, two
  stored claims from one observation would look like two claims.
- **Hedges and plans are frequent.**
  - **Hedges:** 4 of the 31 expected candidates are hedged.
  - **Plans:** 3 are planned.
  - **What is lost if they are formed into ordinary claims:** the source's commitment, and the fact that
    nothing has happened yet.
- **Unread time phrases** ("last spring", "next month") must be kept somewhere, because a claim cannot hold
  them.
- **Corrections name their target** only as an earlier *candidate*. To become a supersession suggestion,
  the target must be traced to the claim it became.

## 2. Minimum fields to form one validated candidate into one accepted claim
"Accepted" here means recorded as a claim and then accepted by review: formation itself always creates a
hypothesis.

| Needed on the claim | Have it today? | Why it is the minimum |
|---|---|---|
| type, role players (resolved referents), evidence (observation and passage span) | yes | the claim itself |
| valid-time bounds, time precision, valid-to basis | yes | answers (v1, v2) |
| polarity | yes (core/0010) | negations |
| method (`rules:v2`), extraction basis | yes | provenance |
| **valid-from basis** (`stated`, `lower-bound`, `unknown`) | no | keeps "since" distinct after formation (A1) |
| **commitment** (`certain`, `probable`, `possible`, `unknown`) | no | a hedged candidate formed as a claim must not read as certain |
| **attribution mode** and **asserted by** (a referent) | no | reported, forwarded and rumoured claims must not read as the author's own; corroboration must count distinct asserters |
| **a link to the candidate it came from** | no | trace a claim to the candidate's passage, time readings (A7) and relations |

**Not needed yet:**
- **`modality` on claims.** Formation should form **only `actual` candidates**. Planned, hypothetical and
  other non-actual candidates stay candidates. A plan is never answered as a fact.
- **`transmission` on claims.** It can stay in the candidate payload until a question needs it.
- **A full decomposition of candidates** into TypeDB types (times, participants). The payload keeps them
  exactly.

## 3. Minimum storage for candidates
Formation needs candidates to persist, for three reasons:
- non-actual and unread items must survive
- corrections need targets
- claims need a link back to their source

The smallest form:
- **`memory-candidate`:** `gupi-id @key`, `ir-version`, `candidate-payload` (the exact JSON), `method`,
  `recorded-at`, and `proposition-key` (indexed, for finding candidates about a proposition)
- **`candidate-of`:** candidate to observation
- **`formed-into`:** candidate to claim
- **`correction-suggestion`:** a candidate's stated correction, linking the claim formed from it to the claim
  its target became. It is **a suggestion for review only**. A supersession is still made only by
  `Memory.supersede` (ADR 0006).

`candidate-relation` (general relations between stored candidates) can wait. `repeats` is enough within
one observation's payload for now.

## 4. A revised core/0011 for decision
The recommendation is to split the earlier proposal in two. Both parts are additive, and neither changes
existing claims, ids or keys.

| Migration | Contents | Needed for |
|---|---|---|
| **0011 claim provenance** | `valid-from-basis`, `commitment`, `attribution-mode` (each `@values`, single-valued); relation `assertion` (asserter referent, asserted claim) | forming 6B candidates without losing meaning |
| **0012 candidate store** | `memory-candidate`, `candidate-of`, `formed-into`, `correction-suggestion` | keeping candidates, and tracing claims to them |

**Deferred:** `modality` and `transmission` on claims, and `candidate-relation`.

**Owner decisions needed before 6C starts:**
1. Approve 0011 and 0012 as above, or the original single core/0011.
2. Confirm that only `actual` candidates are formed, and that non-actual ones stay candidates.
3. Confirm that hedged candidates (`probable`, `possible`) are formed, with their commitment recorded.
   The alternative is to keep only `certain` ones.
4. Confirm that corrections become review suggestions only.

## 5. Unchanged
These stay as they are until the decisions above:
- production ingestion and `rules:v1`
- answer semantics v1 (the default) and v2
- the frozen benchmarks
- the budget ledger

The Phase 6D evaluation plan stays provisional. No Phase 5 rerun until formation works end to end, and no
paid LLM use without approval.
