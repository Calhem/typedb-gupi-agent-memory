# Joined spells and truth semantics: analysis against ADR 0007

Date: 2026-11-03. Status: **analysis and proposal. No behaviour has been changed.** Checked against
`main` (`a6d5539`) and `answering.evaluate`. Every "GUPI today" result below was produced by running the
current code on the stated claims.

## Summary
GUPI does treat separate periods as continuous truth: an assembled spell answers **TRUE**, indistinguishable
from direct evidence to callers that read only the answer. The investigation also found three pre-existing
defects in the same-spell rule (ADR 0006/0007) that are more serious: **reinstatement is broken**. After a
recorded termination, a later reinstatement can never be answered TRUE, and a reinstatement's start leaks
FALSE back into the earlier spell. A "still true" claim with no stated start never counts as true, even when
it was written, which hides conflicts. All four have one cause: claims are evaluated one at a time, and no
spells are ever built.

## What ADR 0007 and the code do now
- Per claim: `holds_at` gives TRUE inside a claim's certain period, FALSE before its earliest start or after
  its latest end, UNKNOWN otherwise.
- Same-spell rule: a claim's FALSE counts against another claim covering v only if they are "certainly the
  same spell". An end counts against a claim that certainly started before it; a start counts against a claim
  that certainly lasted past it.
- Assembly: if no verdict decides v, a claim certainly started by v plus a claim certainly not ended by v
  give **TRUE**. A note records that this assumes one continuous period.
- Transaction time: only claims believed at the belief time take part. NOT_YET_KNOWN when nothing about
  the proposition was recorded by then.

## Concrete cases (employment of one person at one organisation)
Claims, in HR's words unless stated:
- J1 "joined Jan 2024" (start window Jan)
- L1 "left Mar 2024" (end window Mar)
- J2 "rejoined Jan 2025"
- L2 "left May 2025"
- ONG "since 2023, still true on 1 Feb 2025"
- ONG2 (chat) "still true on 1 Mar 2025"
- CHAT (chat, 1 Jul 2024) "Alice still works there"

| # | Scenario | Believed claims | Asked | GUPI today | Correct (under the proposal below) |
|---|---|---|---|---|---|
| 1a | Continuous evidence, one claim | ONG | Jun 2024 | TRUE (direct) | TRUE |
| 1b | Continuous evidence, two claims | ONG, ONG2 | 15 Feb 2025 | TRUE (**assembled**) | PRESUMED (no single claim covers 15 Feb) |
| 2 | Separate periods, gap unobserved | J1, L2 (the March exit and the rejoin went unrecorded) | Jul 2024 | **TRUE** (assembled) | PRESUMED: false in fact, but no longer shown as direct |
| 3a | Terminated, then reinstated | J1, L1, J2, L2 | 15 Feb 2024 | **FALSE** | PRESUMED (J1 to L1 bracket it) |
| 3b | the same | J1, L1, J2, L2 | Jul 2024 (the gap) | FALSE | FALSE (after L1, before J2) |
| 3c | the same | J1, L1, J2, L2 | Mar 2025 | **FALSE** | PRESUMED (J2 to L2 bracket it) |
| 4 | Conflict inside the gap | J1, L1, J2, L2, CHAT | 1 Jul 2024 | **FALSE** (conflict invisible) | CONTESTED (L1's termination vs CHAT's "still works there") |
| 4′ | the same | the same | 15 Jun 2024 | FALSE | FALSE (CHAT says nothing about 15 Jun) |
| 5a | As of 15 Feb 2024 (only J1 recorded) | J1 | 15 Feb 2024 | UNKNOWN | UNKNOWN (end not yet known) |
| 5b | As of 1 Jun 2024 (J1, L1 recorded) | J1, L1 | 15 Feb 2024 | TRUE (assembled) | PRESUMED |
| 5c | As of 1 Jun 2024 | J1, L1 | Jul 2024 | FALSE | FALSE |
| 5d | As of 1 Jan 2024 | nothing yet | any | NOT_YET_KNOWN | NOT_YET_KNOWN |

**Defects found:**
- **D1 (asked about): presumption shown as TRUE** (1b, 2, 5b).
- **D2: a termination is final** (3c). L1's FALSE "after March 2024" counts against J1 (same spell) and
  applies to all later time, so it defeats the reinstated spell J2 to L2.
- **D3: a later start leaks backwards** (3a). J2's "not before Jan 2025" counts because L2, whose start is
  unstated, could be J2's spell, and it overrides the earlier spell.
- **D4: "still true" without a start never holds** (4). CHAT certainly held on 1 July 2024, but its certain
  period is empty because its start is unknown, so the conflict with L1 is never seen.

Correct today: 1a, 3b, 4′, 5a, 5c, 5d.

## Proposed truth semantics (v2), for approval
**Spells first.** For one proposition, after accepted identities merge referents:
1. Take the believed claims, then collect **boundaries**: each claim's start window (if stated), its end
   window (if stated), and for "still true at observation" claims a point where it is certainly true.
2. Order boundaries in time. A **spell** runs from a start to the next end. Overlapping windows or competing
   boundaries from different sources leave that stretch uncertain.
3. A single claim that states both its start and either its end or "still true at observation" covers its
   own certain period **directly**. Two different claims joined into one spell cover the stretch between them
   only **by presumption**.

**Outcomes at valid time v, as believed at transaction time t** (the "applicable truth policy" is the
default policy below; other policies, such as one ranking source authority, would be explicit options):

| Outcome | Precise meaning |
|---|---|
| NOT_YET_KNOWN | Nothing about the proposition had been recorded by t. (Unchanged; a transaction-time outcome.) |
| CONTESTED | Believed claims give **direct** TRUE and **direct** FALSE for v (e.g. a still-true observation inside a recorded gap), and the policy does not resolve them. |
| TRUE | Some single believed claim directly covers v: its own stated start is before v, and its own stated end, or still-true observation, is after v. |
| FALSE | v lies after a stated end and before the next stated start (or before the first stated start, or after the last stated end), and no claim directly covers v. Under the default policy, a stated end means "not true from then until a later stated start". |
| PRESUMED | v lies inside a spell joined from different claims (a start and a later end, with no boundary between), and no claim directly covers or excludes v. Shown with the claims joined and the assumption "no unrecorded break". |
| UNKNOWN | Claims were recorded by t, but none of the above applies: unstated bounds, uncertain windows, or only hypotheses, rejected or retracted claims. |

The precedence when several apply is NOT_YET_KNOWN, then CONTESTED, then TRUE, then FALSE, then PRESUMED,
then UNKNOWN. FALSE outranks PRESUMED because direct evidence beats an assumption: if one source brackets
Jan-May and another says she left in March, April is FALSE (noting the overridden presumption), not
CONTESTED. CONTESTED is reserved for direct-versus-direct disagreement, as in ADR 0006.

**Consistency with existing semantics.**
- The categories are mutually exclusive under that precedence, and exhaustive (UNKNOWN is the remainder).
- NOT_YET_KNOWN keeps its meaning (transaction time). PRESUMED is the only new value.
- TRUE becomes *stricter*: it now means direct support. Every v1 TRUE that came from one claim stays TRUE;
  assembled TRUEs become PRESUMED.
- FALSE becomes *bounded* by the next stated start (fixes D2) and no longer leaks backwards (fixes D3).
- "Still true at observation" now certainly holds at the observation time (fixes D4). This needs no data
  migration: it is an interpretation of stored bounds (`valid-to-basis "ongoing-at-observation"`), applied
  at answer time.
- ADR 0006's conflict classes are compatible: CONTESTED corresponds to "contradiction"; "separate periods"
  becomes a computed consequence of spells.
- The same-spell rule (ADR 0006/0007) is **replaced** by spell construction; its stated intent ("a FALSE
  counts only against the same spell") is kept and made exact.
- Open-role questions: an overall answer follows the same precedence; a PRESUMED candidate is listed as such.
- Value-filtered questions (ADR 0007): claims without the value still contribute only boundaries that end
  spells, never TRUE or PRESUMED.

## What would change if approved

| Area | Effect |
|---|---|
| Code | `gupi.temporal.Answer` gains PRESUMED; `gupi.answering.evaluate` builds spells; `query._overall`, `query.SUPPORT` (citations for PRESUMED = the joined claims), CLI output, `retrieval_eval` scoring |
| Tests pinned to v1 | `tests/unit/test_spells.py` (assembly → PRESUMED), `tests/integration/test_server_filtering.py::test_joined_and_left_are_assembled_into_one_spell`, Phase 3 `test_conflicts.py::test_separate_periods_are_not_contested` and the temporal tests: rechecked under v2, with every expectation change listed in the change's commit; new regression tests for cases 1-5 |
| Frozen results | Phase 2-5 results stay as committed (v1). Under v2, Phase 4 `q01` would become PRESUMED (gold TRUE); a v2 re-run would be reported separately, never replacing the first run. Phase 5 is retrieval-only and unaffected. |
| Data | No schema migration and no stored-data change; answers are computed. |
| API | An explicit answer-semantics version (`v1` today, `v2` proposed) on `ask`/`query`, recorded in every result, default unchanged until approved |
| Docs | ADR 0003 (answer table), ADR 0006 (same-spell rule superseded), ADR 0007 (spell assembly), README example ("presumed") |

**Recommended ADR change:** a new ADR 0009, "Spell-based truth semantics (v2)", which supersedes ADR 0007's
spell-assembly section and ADR 0006's same-spell rule, records the outcomes and precedence above, and keeps
v1 documented for reproducing past results. ADRs 0006 and 0007 get a one-line pointer to it, and nothing
else is edited.

## Decisions needed
1. Approve the v2 outcomes and precedence (in particular PRESUMED as a distinct outcome, FALSE outranking
   PRESUMED, and CONTESTED only for direct-versus-direct disagreement).
2. Approve versioned semantics with v1 kept for past results, and ADR 0009 as the place to record it.
3. Approve adding regression tests for cases 1-5 now as known failures (`xfail`) under v1, to be turned on by
   the v2 implementation. (Not done yet: this changes the test suite, so it waits for approval.)
