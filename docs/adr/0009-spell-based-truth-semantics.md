# ADR 0009: Spell-based truth semantics (v2)

Status: **proposed (2026-11-03), not accepted, not implemented.** Until accepted, ADR 0003, ADR 0006 and
ADR 0007 describe the behaviour in force (v1).

## Context
The v1 rules evaluate each claim separately, then combine verdicts with the same-spell rule and spell
assembly (ADR 0006, 0007). The analyses in `docs/specialist/joined-spell-analysis.md` and
`docs/specialist/v2-truth-semantics.md` show four defects:
- **D1:** a spell joined from two claims is answered TRUE, as if directly supported.
- **D2:** a termination defeats a later reinstatement (FALSE, or CONTESTED, where it should be TRUE or
  presumed).
- **D3:** a reinstatement's start leaks FALSE into an earlier spell.
- **D4:** a "still true" claim without a stated start never holds, which hides conflicts.

v1 also treats a stated start as FALSE for all earlier time, i.e. absence of a spell as negative evidence.

## Decision (proposed)
1. **Evidence first, in order:**
   1. Filter to claims believed at the belief time t (ADR 0003, 0006 unchanged).
   2. Derive valid-time evidence: positive spans (one claim's own certain period), positive points ("still
      true at o"), terminations, explicit negations, starts.
   3. Classify each requested instant with a decision table over the evidence present.

   There is no global precedence between outcomes.
2. **FALSE needs applicable negative evidence:** a termination (until the next stated start), or an explicit
   negation. A start, and the absence of a positive spell, are not negative evidence.
3. **Outcomes:**
   - TRUE (direct positive evidence)
   - **PRESUMED** (inside a spell joined from different claims; new)
   - FALSE (applicable negative evidence)
   - CONTESTED (direct positive and direct negative evidence for the same instant)
   - UNKNOWN (claims recorded, nothing decides)
   - NOT_YET_KNOWN (nothing recorded by t; unchanged)
4. **Intervals** are asked in a stated mode: at an instant, throughout an interval, or at some time in it.
   Aggregation rules are in v2-truth-semantics.md §3.
5. **Versioned semantics:** `ask` and `query` take an answer-semantics version; v1 remains available, and the
   default until this ADR is accepted. Every result records the version that produced it.
6. The open questions Q1-Q8 in v2-truth-semantics.md are resolved as part of accepting this ADR. The
   recommended resolutions are listed there.

## Consequences
- **Supersedes, on acceptance:** ADR 0007's spell-assembly section and ADR 0006's same-spell rule (both kept
  for v1, with a one-line pointer to this ADR). ADR 0003's answer table gains PRESUMED and the narrower FALSE.
- **Answers that change under v2:** joined spells become PRESUMED; reinstated spells are answered correctly;
  first-spell FALSE from a later start disappears; "still true" points hold at their observation time;
  before a first start, FALSE becomes UNKNOWN (Q1); competing end statements become CONTESTED (Q2).
- **Reproducibility:** committed Phase 2-5 results are v1 and are not rewritten. Re-running a frozen
  benchmark under v2 is reported as a separate run; the Phase 4 benchmark keeps v1, and its `q01` would read
  PRESUMED under v2.
- **Data:** no schema migration (answers are computed), except a polarity attribute if Q4 is accepted, which
  would be a numbered migration (ADR 0004).
- **Tests:** v1 tests stay and run under v1. v2 adds regression tests for truth-table rows R1-R15, plus a
  spell-construction suite.
- **M1** uses v2 only after this ADR and its tests are approved (owner condition).
