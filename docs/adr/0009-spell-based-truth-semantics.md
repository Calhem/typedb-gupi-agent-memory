# ADR 0009: Spell-based truth semantics (v2)

Status: **proposed; directions approved (2026-11-03); implemented behind `semantics="v2"` on branch
`feature/v2-temporal-semantics`; not accepted.** v1 remains the default. The owner approved
the directions for Q1-Q8, with clarifications on Q3 and Q6 and a requirement that explicit negations are
independent of termination dates. Until this ADR is accepted, ADR 0003, ADR 0006 and ADR 0007 describe the
behaviour in force (v1).

## Context
The v1 rules evaluate each claim separately, then combine verdicts with the same-spell rule and spell
assembly (ADR 0006, 0007). The analyses in `docs/specialist/joined-spell-analysis.md` and
`docs/specialist/v2-truth-semantics.md` show four defects:
- **D1:** a spell joined from two claims is answered TRUE, as if directly supported.
- **D2:** a termination defeats a later reinstatement (FALSE, or CONTESTED, where it should be TRUE or
  presumed).
- **D3:** a reinstatement's start leaks FALSE into an earlier spell.
- **D4:** a "still true" claim without a stated start never holds, which hides conflicts.

v1 also treats a stated start as FALSE for all earlier time, i.e. absence of a spell as negative evidence. It
cannot express an explicit negation at all.

## Decision (proposed)
1. **Evidence first, in order:**
   1. Filter to claims believed at the belief time t (ADR 0003, 0006 unchanged). Corrections act here.
   2. Derive valid-time evidence items, each with a polarity: positive spans, positive points, terminations,
      explicit negations; starts are boundaries only.
   3. Combine statements about the same boundary, then classify each requested instant by its certain
      coverage, with the decision table in v2-truth-semantics.md §2.

   There is no global precedence between outcomes.
2. **FALSE needs applicable negative evidence:** an explicit negation covering v, or a termination that is
   still effective. A start, and the absence of a positive spell, are not negative evidence (Q1).
3. **Terminations (Q3):** a recorded termination stays effective until a documented reinstatement or
   correction. A reinstatement ends it where the reinstatement may have begun; a correction removes it at
   the belief cutoff. FALSE on this basis is a **belief-policy default, not certainty about unobserved
   events**. It is labelled `termination-continuing` and explained as such.
4. **Explicit negations (Q4)** are evidence items with negative polarity and their own stated coverage,
   independent of termination dates. They create no end bound and are never continued forward. Storing
   them needs a polarity attribute (a numbered migration, ADR 0004). Until then they are reported as
   unrepresented, never converted into ends.
5. **Overlap (Q6):** overlapping windows and evidence are evaluated by compatibility and temporal coverage.
   - Compatible statements about the same boundary narrow it.
   - Compatible statements about different boundaries are ordered.
   - Incompatible certain coverage is CONTESTED at exactly the conflicting instants.
   - Overlap alone never implies UNKNOWN. UNKNOWN means no certain evidence covers v and v lies in an
     uncertainty window that could change the answer, or nothing covers v.
6. **Outcomes:**
   - TRUE (direct positive coverage)
   - **PRESUMED** (inside a spell joined from different claims; new)
   - FALSE (applicable negative coverage)
   - CONTESTED (positive and negative coverage of the same instant, including competing ends, Q2)
   - UNKNOWN (claims recorded, nothing decides)
   - NOT_YET_KNOWN (nothing recorded by t; unchanged)
7. **Every result records a basis:**
   - `direct-span`, `direct-point`
   - `joined-spell`
   - `negation`, `termination-continuing`
   - `conflict`
   - `window`, `no-coverage`
   - `not-recorded`, `not-believed`

   The basis names the claims involved.
8. **Point evidence (Q5):** "still true at o" and "not true at o" are points. Joining does the rest.
9. **Intervals (Q7)** are asked in a stated mode: at an instant, throughout an interval, or at some time in
   it. Aggregation rules are in v2-truth-semantics.md §3.
10. **No source authority in v2 (Q8).** CONTESTED stays contested; authority is a later, explicit policy.
11. **Versioned semantics:** `ask` and `query` take an answer-semantics version. v1 remains available, and is
    the default until this ADR is accepted. Every result records the version that produced it.
12. **Competing start statements (Q9),** decided by the owner on 2026-11-03, are judged claim by claim.
    - **Each start claim stands alone:** it keeps its own window, precision, provenance and belief time, and
      is judged for the instant asked:
      - **supports:** it certainly started by then, and the period is evidenced to continue past it
      - **contradicts:** its whole window is after the instant, so it dates the start of that same period
        later
      - **imprecise:** its window contains the instant
      - **silent:** it started by then, but nothing shows the period continuing
    - **The outcome:**
      - Something supports and something contradicts: **CONTESTED**.
      - Something supports and something is imprecise: **UNKNOWN**, because the date is too imprecise to
        decide.
      - All support: **that state**, disclosing the disputed start.
      - Nothing supports: the **ordinary rules**, so a start alone is still never negative (Q1).
    - **Never assumed:** the true start is never assumed to lie between the dates, and neither date is
      preferred.

## Consequences
- **Supersedes, on acceptance:** ADR 0007's spell-assembly section and ADR 0006's same-spell rule (both kept
  for v1, with a one-line pointer to this ADR). ADR 0003's answer table gains PRESUMED, the narrower FALSE
  and the basis.
- **Answers that change under v2:**
  - joined spells become PRESUMED
  - reinstated spells are answered correctly
  - first-spell FALSE from a later start disappears
  - "still true" points hold at their observation time
  - before a first start, FALSE becomes UNKNOWN (Q1)
  - inside a reinstatement's start window, FALSE becomes UNKNOWN
  - competing end statements become CONTESTED (Q2)
- **Reproducibility:** committed Phase 2-5 results are v1 and are not rewritten. Re-running a frozen
  benchmark under v2 is reported as a separate run. The Phase 4 benchmark keeps v1; its `q01` would read
  PRESUMED under v2.
- **Data:** answers are computed, so no migration is needed, except the polarity attribute for negations
  (Q4).
- **Tests:** truth-table rows R1-R23 are proposed acceptance tests (`tests/acceptance/`).
  - Their v1 column is checked against today's code.
  - Their v2 column is a strict expected failure until v2 exists.
  - v1 tests stay and run under v1.
- **M1** uses v2 only after this ADR and its tests are approved (owner condition).
