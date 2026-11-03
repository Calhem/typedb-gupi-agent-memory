# Truth semantics v2 (revised twice): truth table and decisions

Date: 2026-11-03. Status: **directions approved; implemented in `gupi.answering_v2`, selected with
`semantics="v2"`; v1 is the default.** Phase 4 under v2: docs/evaluation/phase-4-v2.md. The second revision adopts the
owner's decisions on Q1-Q8 (§5), including the clarifications on Q3 and Q6 and the requirement that
explicit negations are represented independently of termination dates.

The conditions from the first review still hold:
- no global outcome precedence
- evidence filtered to the belief cutoff and the requested valid time before classifying
- FALSE only with applicable negative evidence
- correct handling of reinstatement, corrections, conflicts, out-of-order arrival and as-of history
- NOT_YET_KNOWN kept distinct from UNKNOWN

The rows R1-R23 (§4) are written as **proposed acceptance tests** in `tests/acceptance/test_v2_truth_table.py`.
There, the v1 column is checked against today's code, and the v2 column is recorded as an expected failure
until v2 exists.

## 1. Procedure
For a question about one proposition, an instant v (or an interval [a, b)) and a belief time t:

1. **Belief cutoff (transaction time).** Keep the claims believed at t: recorded by t, latest review an
   acceptance, and no supersession in force (ADR 0006).
   - If no claim about the proposition had been *recorded* by t (believed or not): **NOT_YET_KNOWN**. Stop.
   - A correction acts here: a superseded or rejected claim is no longer evidence. Arrival order matters only
     at this step; valid-time order never depends on it.
2. **Evidence in valid time.** From the kept claims, derive evidence items. Each item names its claim and
   has a polarity (positive or negative).

   | Item | Polarity | Certain coverage |
   |---|---|---|
   | Positive span | + | the claim's own certain period: from its stated start's latest bound to its stated end's earliest bound, or to its "still true" observation |
   | Positive point | + | the observation instant o of a "still true at o" claim, even with no stated start (Q5) |
   | Termination | − | from the end's latest bound, continuing until a later recorded start may have begun (Q3, §1.3) |
   | Negation | − | only the time the negation itself states: a point ("does not work there", said at o) or a span ("has not worked there since March"). It is never continued forward (§1.4). |
   | Start | none | a start is a boundary, not negative evidence for earlier times (Q1) |

3. **Boundaries and coverage (Q3, Q6).**
   - **Statements about the same boundary are combined before anything is classified.** Two stated starts
     with no recorded end between them describe the same start; two stated ends with no recorded start
     between them describe the same end.
     - If their windows overlap, they are compatible. The boundary lies in the intersection, so the
       uncertainty narrows (R20, R23).
     - If their windows are disjoint, the statements compete. For ends, the instants between them are
       CONTESTED (Q2). For starts, see open question Q9.
   - **A termination stays effective** until a documented reinstatement or correction (Q3).
     - A correction removes it at step 1.
     - A reinstatement (a later stated start) ends its negative coverage where the reinstatement *may* have
       begun, at the start's earliest bound. Instants inside the reinstatement's start window are therefore
       not FALSE (R22).
   - **A joined spell** runs from a start in one claim to a later stated end or positive point in another,
     with no termination between them. Its interior is presumed, not directly supported.
   - **Overlap is not a reason for UNKNOWN (Q6).** Overlapping windows and evidence are evaluated by
     compatibility and coverage. Each instant is classified by what certainly covers it. An instant is
     UNKNOWN only when no certain evidence covers it and it lies in an uncertainty window that could change
     the answer.
     - An end window overlapping the next start window is compatible: ended, then restarted. Where a span
       certainly covers an instant, that decides it (R21).
     - Evidence that cannot all hold at once (a positive and a negative item certainly covering the same
       instant) is a conflict: CONTESTED at exactly those instants.
4. **Explicit negations are separate from terminations.**
   - A negation is its own evidence item with negative polarity and its own stated coverage. It creates no
     end bound and needs no preceding start.
   - It is not continued forward: "does not work there as of 1 July" says nothing about 1 August (R17).
     Negative points mirror positive points (Q5).
   - It can conflict with positive evidence without any termination involved (R18, R19).
   - It needs a polarity attribute (Q4; a numbered migration in the formation milestone). Until then, a
     negation is **not** stored as a claim and is not converted into an end date. Extraction records it as
     unrepresented in the run report, so the loss is visible and counted. This replaces the earlier interim
     proposal to model negations as ends.
5. **Classify each instant** with §2; for an interval, aggregate by the stated mode (§3).

## 2. Classification at an instant v
P = certain positive coverage at v · N = certain negative coverage at v · J = v lies inside a joined spell ·
W = v lies inside the (narrowed) uncertainty window of a boundary that could change the answer at v.

| P | N | J | W | Result | Basis recorded with the result |
|---|---|---|---|---|---|
| yes | yes | any | any | **CONTESTED** | the positive and negative items in conflict |
| yes | no | any | any | **TRUE** | `direct-span` or `direct-point`: the claim(s) |
| no | yes | any | any | **FALSE** | `negation` (the negation covers v), or `termination-continuing` (see below) |
| no | no | yes | no | **PRESUMED** | `joined-spell`: the joined claims, with the assumption "no unrecorded break" |
| no | no | yes or no | yes | **UNKNOWN** | `window`: the boundary whose window contains v |
| no | no | no | no | **UNKNOWN** | `no-coverage` |

Competing end statements (Q2) produce both P (the later end's joined spell) and N (the earlier end's
termination) on the instants between them, so they fall in the first row.

Before the table applies: NOT_YET_KNOWN when nothing was recorded by t (`not-recorded`), and UNKNOWN when
something was recorded but nothing is believed (`not-believed`). These are the ADR 0003 meanings, unchanged.

This is a decision table over the evidence present at v, not a precedence over outcomes.

**FALSE from a continuing termination is a belief-policy outcome (Q3).**
- It means "a termination was recorded and no reinstatement or correction had been recorded by t". It does
  not mean that anyone observed the person's absence at v.
- Every such result carries the basis `termination-continuing`, the terminating claim and t. Its
  explanation says so in words, for example: "FALSE: recorded as having left in March 2024 (L1); no
  reinstatement or correction recorded by 15 Sep 2024. This is a default, not an observation at 15 Jul 2024."
- The answer label stays FALSE, so that answers remain comparable. Scoring and display must use the basis to
  tell it apart from FALSE by `negation`, which is a direct statement about v.

## 3. Interval questions [a, b) (Q7)
The question states its mode; M1 questions must state it.
- **at v:** the table above.
- **throughout [a, b):**
  - TRUE if every instant is TRUE.
  - CONTESTED if any instant is CONTESTED.
  - FALSE if some instant is FALSE and none is CONTESTED.
  - PRESUMED if every instant is TRUE or PRESUMED, and some are PRESUMED.
  - Otherwise UNKNOWN.
- **at some time in [a, b):**
  - TRUE if any instant is TRUE.
  - FALSE if every instant is FALSE.
  - CONTESTED if the only positive instants are CONTESTED.
  - PRESUMED if some instant is PRESUMED and none is TRUE.
  - Otherwise UNKNOWN.

A FALSE or TRUE interval answer lists the bases of the instants that decided it.

## 4. Truth table (proposed acceptance tests)
Valid-time evidence, one person at one organisation:

| Id | Statement | Evidence |
|---|---|---|
| J1 | "joined Jan 2024" | start window [1 Jan, 1 Feb 2024) |
| J1x | "joined on 10 Jan 2024" | start window [10 Jan, 11 Jan 2024) |
| L1 | "left Mar 2024" | end window [1 Mar, 1 Apr 2024) |
| L1b | "left on 20 Mar 2024" | end window [20 Mar, 21 Mar 2024) |
| K | "Correction: she left in February, not March" | end window February; supersedes L1 |
| CHAT | "Alice still works there" | positive point 1 Jul 2024 |
| NEG | "Alice does not work there" | negation point 1 Jul 2024 |
| NEGS | "Alice has not worked there since March 2024" (said 1 Sep 2024) | negation span [1 Apr, 1 Sep 2024) |
| J3 | "rejoined in spring 2024, still there on 1 Sep 2024" | start window [1 Mar, 1 Jun 2024); positive to 1 Sep 2024 |
| J2 | "rejoined Jan 2025" | start window January 2025 |
| J2D | "rejoined Jan 2025, still there 1 Mar 2025" | start window January 2025; positive to 1 Mar 2025 |
| L2 | "left May 2025" | end window May 2025 |
| ONG | "since 2023, still true 1 Feb 2025" | start window 2023; positive to 1 Feb 2025 |
| ONG2 | "still true 1 Mar 2025" | positive point 1 Mar 2025 |

Recording (belief) times:
- J1 on 21 Jan 2024
- CHAT on 1 Jul 2024
- L1 on 1 Sep 2024: arrives late, after CHAT
- K on 1 Oct 2024
- J2 and J2D on 20 Jan 2025
- L2 on 2 Jun 2025
- the others when said

"v1" is today's code's output, measured by the acceptance tests. "v2" is the proposal.

| Row | Behaviour | Believed at t | v | v1 (today) | v2 | Basis (v2) and why |
|---|---|---|---|---|---|---|
| R1 | D1 continuous, joined | ONG, ONG2 | 15 Feb 2025 | TRUE (assembled) | **PRESUMED** | joined-spell ONG→ONG2: ONG's span ends 1 Feb; ONG2 is a point on 1 Mar |
| R2 | D1 unobserved gap | J1, L2 | 1 Jul 2024 | TRUE (assembled) | **PRESUMED** | joined-spell J1→L2; an unrecorded gap is labelled, not detected |
| R3 | D2 reinstatement, joined | J1, L1, J2, L2 | 15 Mar 2025 | FALSE | **PRESUMED** | joined-spell J2→L2; L1's coverage ended where J2 may have begun |
| R4 | D2 reinstatement, direct | J1, L1, J2D | 15 Feb 2025 | CONTESTED | **TRUE** | direct-span J2D; L1's coverage ended at J2D's start |
| R5 | D3 first spell | J1, L1, J2, L2 | 15 Feb 2024 | FALSE | **PRESUMED** | joined-spell J1→L1; J2's start is not negative evidence for 2024 |
| R6 | gap after termination | J1, L1, J2, L2 | 15 Jul 2024 | FALSE | **FALSE** | termination-continuing L1 (no reinstatement until J2 in 2025) |
| R7 | D4 conflict inside the gap | J1, L1, J2, L2, CHAT | 1 Jul 2024 | FALSE | **CONTESTED** | CHAT (+) vs L1 (−) at the same instant |
| R8 | D4, outside the conflict point | same | 15 Jun 2024 | FALSE | **FALSE** | termination-continuing L1; CHAT says nothing about 15 Jun |
| R9 | out-of-order, before L1 arrived | J1, CHAT (t = 1 Aug 2024) | 1 Jul 2024 | UNKNOWN | **TRUE** | direct-point CHAT; L1 not yet recorded |
| R10 | as-of, before L1 arrived | J1, CHAT (t = 1 Aug 2024) | 1 May 2024 | TRUE (assembled) | **PRESUMED** | joined-spell J1→CHAT |
| R11 | as-of, after L1 arrived | J1, L1, CHAT (t = 15 Sep 2024) | 1 May 2024 | FALSE | **FALSE** | termination-continuing L1, as believed on 15 Sep 2024 |
| R11b | the same | J1, L1, CHAT (t = 15 Sep 2024) | 1 Jul 2024 | FALSE | **CONTESTED** | CHAT (+) inside L1's coverage (−) |
| R12 | correction (K supersedes L1) | J1, K, CHAT (t = 15 Oct 2024) | 20 Feb 2024 | TRUE (assembled) | **UNKNOWN** | window: K's end window (February) |
| R12′ | the same, as believed before K | J1, L1, CHAT (t = 15 Sep 2024) | 20 Feb 2024 | TRUE (assembled) | **PRESUMED** | joined-spell J1→L1; history preserved |
| R13 | nothing recorded yet | none (t = 1 Dec 2023) | any | NOT_YET_KNOWN | **NOT_YET_KNOWN** | not-recorded |
| R14 | recorded, not believed | J1 recorded, unreviewed (t = 25 Jan 2024) | 15 Feb 2024 | UNKNOWN | **UNKNOWN** | not-believed |
| R15 | before the first start | J1 | 15 Dec 2023 | FALSE | **UNKNOWN** | no-coverage: a start is not negative evidence (Q1) |
| R16 | negation, no termination | J1, NEG | 1 Jul 2024 | UNKNOWN (NEG not stored) | **FALSE** | negation NEG: direct, no end date involved |
| R17 | a negation is not continued | J1, NEG | 1 Aug 2024 | UNKNOWN (NEG not stored) | **UNKNOWN** | no-coverage: NEG covers 1 Jul only |
| R18 | negation vs positive point | J1, CHAT, NEG | 1 Jul 2024 | UNKNOWN (NEG not stored) | **CONTESTED** | CHAT (+) vs NEG (−) |
| R19 | negation span vs open span | ONG, NEGS | 1 Jun 2024 | TRUE (NEGS not stored) | **CONTESTED** | ONG (+, 2024 to 1 Feb 2025) vs NEGS (−, Apr to Sep 2024) |
| R19b | after the negation's coverage | ONG, NEGS | 1 Oct 2024 | TRUE (NEGS not stored) | **TRUE** | direct-span ONG; NEGS ends at 1 Sep and is not continued |
| R20 | Q6 same start, compatible windows | J1, J1x, CHAT | 20 Jan 2024 | TRUE (assembled) | **PRESUMED** | joined-spell J1x→CHAT; J1's window narrows to J1x's, so 20 Jan is not in a window |
| R21 | Q6 end window overlaps restart window | J1, L1, J3 | 1 Jul 2024 | CONTESTED | **TRUE** | direct-span J3 (1 Jun to 1 Sep); compatible order, end then restart |
| R22 | the same, uncovered instant | J1, L1, J3 | 15 Apr 2024 | FALSE | **UNKNOWN** | window: J3's start window (may have rejoined); L1's coverage ended at 1 Mar |
| R23 | Q6 same end, compatible windows | J1, L1, L1b | 25 Mar 2024 | FALSE | **FALSE** | termination-continuing L1b; L1's window narrows to 20 Mar |

What the rows show:
- **D1-D4:** v2 fixes D1 (R1, R2, R10), D2 (R3, R4), D3 (R5) and D4 (R7, R9, R11b).
- **v1 results kept:** R6, R8, R11, R13, R14 and R23; R11 also gains a basis.
- **Correction:** R12 is now honest.
- **Changed v1 answers:**
  - R15 changes from FALSE to UNKNOWN (Q1).
  - R22 changes from FALSE to UNKNOWN, because a documented reinstatement may already have begun.
- **Negation (R16-R19b):** v1 cannot store a negation, so its answers ignore it (R16, R18 and R19 are wrong in v1). Negations become representable after the polarity migration; until then they are reported as unrepresented.
- **Q6 (R20-R23):** overlap does not imply UNKNOWN. Compatible windows narrow or order the boundaries, and
  certain coverage decides. UNKNOWN comes only from an instant no evidence certainly covers (R22).

## 5. Decisions
| # | Question | Decision (2026-11-03) |
|---|---|---|
| Q1 | Is a stated start negative evidence for earlier times? | **No**: UNKNOWN before the first start (R15). |
| Q2 | Competing end statements | **CONTESTED** between them; both are direct statements about the same boundary. |
| Q3 | How long does a termination stay negative? | **Until a documented reinstatement or correction**, as a belief-policy default. It is never presented as certainty about unobserved events: basis `termination-continuing`, with an explanation (§2). |
| Q4 | Explicit negations | **Polarity attribute**, a numbered migration in the formation milestone. Negations are their own evidence items, independent of termination dates (§1.4). Until then they are not stored as claims and are reported as unrepresented. |
| Q5 | "Still true at o" with no start | **Point only**; joining does the rest. Negative points behave the same way. |
| Q6 | Overlapping windows and evidence | **Evaluated by compatibility and coverage** (§1.3). Overlap alone never implies UNKNOWN. |
| Q7 | Interval modes | **All three** (at / throughout / at some time in); each M1 question states its mode. |
| Q8 | Source authority | **None in v2**: CONTESTED stays contested; authority is a separate, explicit policy later. |

### Open question (new, from the Q6 work)
| # | Question | Options | Recommendation |
|---|---|---|---|
| Q9 | Competing *start* statements with disjoint windows ("joined January" vs "joined March", no end between them): what about February? | (a) UNKNOWN, a start window covering the hull of both; (b) CONTESTED, as for ends (Q2); (c) PRESUMED from the earlier start, with a conflict flagged | **(a)**, with a conflict flagged. Under Q1 a start is not negative evidence, so the March statement does not directly deny February; CONTESTED needs direct negative evidence. Not needed for R1-R23. |

## 6. Implementation notes
These are rules the specification leaves implicit. They do not change any row of §4.
- **Which start is "later" than a termination:** a start whose window's earliest bound is not before the
  termination's earliest bound.
- **"Statements about the same boundary"** are consecutive starts, or consecutive ends, after sorting all
  boundaries by window (earliest bound, then latest).
- **Competing ends (Q2):** CONTESTED from the earlier end's latest bound to the later end's earliest bound.
- **Q9 (open):** the provisional rule (a) is implemented, and every affected answer says so in its
  explanation. It changes Phase 4 question q01 (phase-4-v2.md).
- **Bounding claims** (value-filtered questions) contribute only terminations and negations, as in v1.
- **Open-role questions** rank PRESUMED after TRUE when combining candidates.
- **v1 and negations:** v1 cannot express negation, so it reports believed negations as excluded.
- **Interval questions** (§3, Q7) are not implemented. Questions are asked at an instant.

## 7. Compatibility
- **v1 stays available and the default** until v2 is accepted and implemented. Every result records its
  semantics version.
- **Committed results:** Phase 2-5 results are v1 and unchanged. Under v2, the Phase 4 benchmark's `q01` would
  become PRESUMED; that would be reported as a separate v2 run, never replacing the first run.
- **v2 changes existing answers in these situations:**
  - joined spells become PRESUMED
  - reinstated spells are no longer blocked
  - first-spell FALSE caused by a later start disappears
  - "still true" points hold at their observation time
  - before a first start, FALSE becomes UNKNOWN (Q1)
  - inside a reinstatement's start window, FALSE becomes UNKNOWN (R22)
  - competing end statements become CONTESTED (Q2)
- **New output:** every result carries a basis (§2).
- **Schema:** the only change is the polarity migration (Q4).
- **Tests:** R1-R23 are in place as proposed acceptance tests. The tests pinned to v1 are listed in
  joined-spell-analysis.md; each changed expectation would be listed in the v2 commit.
