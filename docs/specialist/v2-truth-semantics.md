# Truth semantics v2 (revised): truth table and open questions

Date: 2026-11-03. Status: **proposal for approval; not implemented.** It revises the v2 proposal in
`joined-spell-analysis.md` with the owner's conditions:
- no global outcome precedence
- evidence filtered to the belief cutoff and the requested valid time before classifying
- FALSE only with applicable negative evidence
- correct handling of reinstatement, corrections, conflicts, out-of-order arrival and as-of history
- NOT_YET_KNOWN kept distinct from UNKNOWN

## 1. Procedure
For a question about one proposition, an instant v (or an interval [a, b)) and a belief time t:

1. **Belief cutoff (transaction time).** Keep the claims believed at t: recorded by t, latest review an
   acceptance, and no supersession in force (ADR 0006).
   - If no claim about the proposition had been *recorded* by t (believed or not): **NOT_YET_KNOWN**. Stop.
   - Arrival order matters only here; valid-time order never depends on it.
2. **Evidence in valid time.** From the kept claims, derive evidence items, each with its own claim:
   - **Positive span:** a single claim's own certain period, from its stated start (latest bound) to its
     stated end (earliest bound), or to its "still true" observation.
   - **Positive point:** a "still true at o" claim is certainly true at o, even with no stated start.
   - **Termination:** a stated end; negative from its latest bound onwards.
   - **Negation:** an explicit "not / no longer" statement; negative from its time onwards. Note that
     today's schema can only express this as an end; see open question Q4.
   - **Start:** a stated start. It is **not** negative evidence on its own (condition 5).
3. **Local spells.** Order the evidence boundaries around the requested time:
   - A **termination's negative evidence** lasts until the next later stated **start** (a reinstatement),
     not forever. This fixes D2. A positive span or point *inside* that range does not end it; it conflicts
     with it, giving CONTESTED at those instants (R7, R11b).
   - A start never creates negative evidence for earlier times. This fixes D3.
   - A **joined spell** runs from a start in one claim to a later end, or positive point, in another claim,
     with no termination between them. Its interior is presumed, not directly supported.
4. **Classify each instant** with the table below; for an interval, aggregate by the requested mode (§3).

## 2. Classification at an instant v
P = some positive span or point covers v · N = some applicable negative evidence covers v ·
J = v lies inside a joined spell · W = v lies inside the uncertainty window of a relevant boundary.

| P | N | J or W | Result |
|---|---|---|---|
| yes | yes | any | **CONTESTED** (direct positive and direct negative for the same instant) |
| yes | no | any | **TRUE** |
| no | yes | J | see open question Q2 (competing end statements); proposed **CONTESTED** |
| no | yes | none or W only | **FALSE** |
| no | no | J (and no W) | **PRESUMED** (names the joined claims; assumes no unrecorded break) |
| no | no | W, or nothing | **UNKNOWN** |

Before the table applies: NOT_YET_KNOWN when nothing was recorded by t, and UNKNOWN when something was
recorded but nothing is believed. These are the existing ADR 0003 meanings, unchanged.

This is a decision table over the evidence present at v, not a precedence over outcomes: each row is one
combination of evidence.

## 3. Interval questions [a, b)
The question states its mode; M1 questions must state it.
- **at v:** the table above.
- **throughout [a, b):** TRUE if every instant is TRUE. FALSE if some instant is FALSE and none is CONTESTED.
  CONTESTED if any instant is CONTESTED. PRESUMED if every instant is TRUE or PRESUMED, and some are PRESUMED.
  Otherwise UNKNOWN.
- **at some time in [a, b):** TRUE if any instant is TRUE. FALSE if every instant is FALSE. CONTESTED if the
  only positive instants are CONTESTED. PRESUMED if some instant is PRESUMED and none is TRUE. Otherwise
  UNKNOWN.

## 4. Truth table for D1-D4 and the required behaviours
Valid-time evidence, one person at one organisation:
- J1 "joined Jan 2024" (start window 1 Jan to 1 Feb 2024)
- L1 "left Mar 2024" (end window 1 Mar to 1 Apr 2024)
- K "Correction: she left in February, not March" (end window February; supersedes L1)
- CHAT "Alice still works there" (positive point 1 Jul 2024)
- J2 "rejoined Jan 2025"
- J2D "rejoined Jan 2025, still there 1 Mar 2025"
- L2 "left May 2025"
- ONG "since 2023, still true 1 Feb 2025"
- ONG2 "still true 1 Mar 2025"

Recording (belief) times:
- J1 on 21 Jan 2024
- CHAT on 1 Jul 2024
- L1 on 1 Sep 2024: arrives late, after CHAT
- K on 1 Oct 2024
- J2, J2D on 20 Jan 2025
- L2 on 2 Jun 2025
- ONG and ONG2 when said

"v1" is the current code's output, measured; "v2" is the expected result under this proposal.

| Row | Defect / behaviour | Believed at t | v | v1 (today) | v2 | Why (v2) |
|---|---|---|---|---|---|---|
| R1 | D1 continuous, joined | ONG, ONG2 | 15 Feb 2025 | TRUE (assembled) | **PRESUMED** | ONG's direct span ends 1 Feb; ONG2 is a point on 1 Mar; between them only a joined spell |
| R2 | D1 unobserved gap | J1, L2 | 1 Jul 2024 | TRUE (assembled) | **PRESUMED** | joined Jan 2024 to May 2025; the real gap is unrecorded, so it is labelled, not detected |
| R3 | D2 reinstatement, joined | J1, L1, J2, L2 | 15 Mar 2025 | FALSE | **PRESUMED** | L1's negative evidence ends at J2's start; J2 to L2 is a joined spell |
| R4 | D2 reinstatement, direct | J1, L1, J2D | 15 Feb 2025 | CONTESTED | **TRUE** | J2D directly covers Jan-Mar 2025; L1's negative evidence ended at J2D's start |
| R5 | D3 first spell | J1, L1, J2, L2 | 15 Feb 2024 | FALSE | **PRESUMED** | J1 to L1 is a joined spell; J2's start is not negative evidence for 2024 |
| R6 | gap after termination | J1, L1, J2, L2 | 15 Jul 2024 | FALSE | **FALSE** | after L1 (1 Apr), before J2 (1 Jan 2025): applicable negative evidence |
| R7 | D4 conflict inside the gap | J1, L1, J2, L2, CHAT (t = now) | 1 Jul 2024 | FALSE | **CONTESTED** | CHAT's positive point vs L1's termination at the same instant |
| R8 | D4, outside the conflict point | same | 15 Jun 2024 | FALSE | **FALSE** | L1's negative evidence; CHAT says nothing about 15 Jun |
| R9 | out-of-order, before L1 arrived | J1, CHAT (t = 1 Aug 2024) | 1 Jul 2024 | UNKNOWN | **TRUE** | CHAT's direct positive point; L1 not yet recorded |
| R10 | as-of, before L1 arrived | J1, CHAT (t = 1 Aug 2024) | 1 May 2024 | TRUE (assembled) | **PRESUMED** | J1 to CHAT joined; nothing negative known yet |
| R11 | as-of, after L1 arrived | J1, L1, CHAT (t = 15 Sep 2024) | 1 May 2024 | FALSE | **FALSE** | L1's termination (from 1 Apr); no later start |
| R11b | the same | J1, L1, CHAT (t = 15 Sep 2024) | 1 Jul 2024 | FALSE | **CONTESTED** | CHAT's positive point inside L1's negative range |
| R12 | correction (K supersedes L1) | J1, K, CHAT (t = 15 Oct 2024) | 20 Feb 2024 | TRUE (assembled) | **UNKNOWN** | v lies inside K's end window (February): ended or not, unknown |
| R12′ | the same, as believed before K | J1, L1, CHAT (t = 15 Sep 2024) | 20 Feb 2024 | TRUE (assembled) | **PRESUMED** | before the correction, J1 to L1 was a joined spell; history preserved |
| R13 | nothing recorded yet | none (t = 1 Dec 2023) | any | NOT_YET_KNOWN | **NOT_YET_KNOWN** | transaction time |
| R14 | recorded, not believed | J1 recorded, unreviewed (t = 25 Jan 2024) | 15 Feb 2024 | UNKNOWN | **UNKNOWN** | recorded but no believed evidence |
| R15 | before the first start | J1 | 15 Dec 2023 | FALSE | **UNKNOWN** (Q1) | a start is not negative evidence; absence of a spell is not FALSE |

The v2 column fixes D1 (R1, R2, R10), D2 (R3, R4), D3 (R5) and D4 (R7, R9, R11b), keeps the correct v1 results
(R6, R8, R11, R13, R14), and makes the correction (R12) and the "before the first start" case (R15) honest.
**R15 changes an existing v1 answer from FALSE to UNKNOWN,** and needs approval (Q1).

## 5. Open questions requiring approval
| # | Question | Options | Recommendation |
|---|---|---|---|
| Q1 | Is a stated start ("joined Jan 2024") negative evidence for earlier times? | (a) no: UNKNOWN before the first start; (b) yes, for a bounded horizon; (c) yes, indefinitely (v1) | **(a)**: the transition implies "not just before", but not for how long. This changes v1 answers before a first start from FALSE to UNKNOWN. |
| Q2 | Competing end statements ("left March" vs "left May", different sources): what about April? | CONTESTED, or FALSE (termination overrides presumption) | **CONTESTED**: both are direct statements about the same boundary |
| Q3 | Does a termination stay negative indefinitely when nothing later is recorded? | indefinitely (v1); or only for a horizon, then UNKNOWN | **indefinitely**: "left and not recorded as returning" is negative evidence; a later start ends it |
| Q4 | Explicit negations ("Alice does not work there as of 1 July") | represent now as an end; or add a polarity attribute (schema migration) | **add polarity** in the formation milestone; until then, model as an end and note the loss |
| Q5 | A "still true at o" claim with no stated start: point only, or presumed back to the last known start? | point only (positive at o; earlier only via a joined spell) | **point only**, with joining doing the rest |
| Q6 | Overlapping boundary windows (an end window overlapping the next start window) | UNKNOWN inside the overlap | **UNKNOWN** |
| Q7 | Interval modes for M1 questions | at / throughout / at some time in | all three, each question stating its mode |
| Q8 | Source authority | none in v2 (CONTESTED stays contested); an authority policy later | **none in v2**: authority resolution is a separate, explicit policy |

## 6. Compatibility
- **v1 stays available and default** until v2 is approved and tested. Every result records its semantics
  version.
- Committed Phase 2-5 results are v1 and unchanged. Phase 4 benchmark under v2: `q01` would become PRESUMED.
  It would be reported as a separate v2 run, never replacing the first run.
- **v2 changes existing answers in these situations:**
  - joined spells become PRESUMED
  - reinstated spells are no longer blocked
  - first-spell FALSE caused by a later start disappears
  - "still true" points now hold at their observation time
  - before a first start, FALSE becomes UNKNOWN (Q1)
  - competing end statements become CONTESTED (Q2)
- **Tests affected:** listed in joined-spell-analysis.md. Each changed expectation would be listed in the v2
  commit, with regression tests R1-R15 added.
- No schema migration is needed, except for Q4 if approved.
