# Phase 6D failure attribution (first run)

**How stages were assigned:** each failure gets its earliest responsible stage, using the stage list in
PLAN.md:

| Stage | Meaning |
|---|---|
| 1 | source absent |
| 2 | extraction missed |
| 3 | extraction misinterpreted |
| 4 | formation withheld, or formed what reviewers had not accepted |
| 5 | stored incorrectly |
| 6 | retrieval missed stored evidence |
| 7 | temporal or evidential reasoning |
| 8 | answer formatting or citation |
| 9 | gold or evaluation ambiguity |

The runner's fixed rules assign stages first. These rules are in `gupi/benchmarks/e2e/world.py`
(`attribute`) and `conversational.py` (`_attribute`). The raw output is in `first-run/*.json`. Manual
reassignments are marked and justified.

## D1: every incorrect or unsupported end-to-end answer
There are two of each: two incorrect answers and two citation failures, on the same two questions. There
are no unsupported definitive answers and no missing answers.

| Question | Gold | GUPI e2e | Rule | Manual | Why |
|---|---|---|---|---|---|
| q01 | TRUE | PRESUMED | 7 | **9, unresolved** | the gold reasons as v1 did, counting a joined period as TRUE; v2 deliberately returns PRESUMED |
| q03 | FALSE | UNKNOWN | 7 | **9, unresolved** | the gold reasons as v1 did, "a later start makes earlier times FALSE"; v2 removed that rule (ADR 0009, Q1) |

**Status: unresolved evaluation disagreements, not proven gold errors.**
- **Why they are open:** the gold answers and GUPI's v2 answers follow different, defensible readings of
  the same evidence.
- **What they are not:** they are not established mistakes in the gold. Nothing in this evaluation shows
  that v2's readings are the right ones; v2's rules are the owner's decisions, not facts about the world.
  No independent annotator has adjudicated either question.
- **What stays as it is:** the frozen gold and the frozen scorer, so both still count as misses (13/15).
- **What would resolve them:** an adjudication by someone independent of GUPI, for example through the
  human trial's guidelines.

**Why each was reassigned from 7 to 9:**
- **Rule 7 is accurate:** "the answer follows from the semantics". The semantics did what the approved
  decisions require.
- **Stage 9 records where the disagreement lies:** between the gold's reasoning and the approved semantics.
  It does not say which side is right.
- **What a stricter reader could say:** that both belong to stage 7, a semantics that disagrees with how the
  question's author reasoned. Either way, neither is an extraction, storage or retrieval failure.

### Trace: q01, "Did Nora Vance work at Halden in mid-March 2025?" (valid 15 March, believed 1 October 2025)
| Message | Source text | rules:v2 candidate | Policy | Stored valid time |
|---|---|---|---|---|
| w1-1 | "Nora Vance joined Halden as CTO in January 2025." | employment, start "January 2025" | formed (formation:v1) | from [1 Jan, 1 Feb 2025) |
| w1-3 | "Nora Vance left Halden in May 2025." | employment, end "May 2025" | formed | to [1 May, 1 Jun 2025) |
| w3-3 | "Since March 2025, Nora Vance works at Halden as CTO." | employment, holds-since "March 2025", holds-at "works" (20 Aug) | formed | held by 1 Apr 2025, to at least 20 Aug |

**The answer:** PRESUMED, citing w1-1 and w1-3, with evidence standing *direct*. The explanation reads:
"inside a period joined from [w1-1] to [w1-3], which no single claim covers; assumes no unrecorded break."

**On gold claims, the answer is UNKNOWN instead:** the Phase 4 world gold encodes w3-3 as a competing start
window in March. End to end differs, because extraction reads w3-3 more weakly, and that removes the
dispute.

### Trace: q03, "Did Leah Ortiz work at Halden in mid-May 2025?"
| Message | Source text | Candidate | Policy | Stored valid time |
|---|---|---|---|---|
| w1-5 | "Leah Ortiz joined Halden as CTO in June 2025." | employment, start "June 2025" | formed | from [1 Jun, 1 Jul 2025) |

**The answer:** UNKNOWN, citing nothing ("no believed evidence covers 2025-05-15"). GUPI on gold claims
gives the same answer.

**Its citation failure, classified:**
- **The failure:** the gold evidence is w1-5, and GUPI cites nothing.
- **The rule:** this is not stage 6, since GUPI on gold claims does not cite w1-5 either (PLAN amendment 1).
- **Where it belongs:** it is part of the same stage-9 disagreement.

### Not a failure, but not tested either: formation without review
- **What the policy formed:** w2-1 ("Ivo Marsh reports to Sam Reed.") and w2-3 ("Pia Holm works at Halden
  as a Designer."). Both are direct, definite assertions, so formation:v1 forms them.
- **What the world records:** w2-1 as rejected, and w2-3 as never reviewed.
- **What the reviewer could do:** under the pre-registered protocol, the simulated reviewer rejected w2-1's
  claim afterwards. w2-3 stays believed.
- **Why the scores do not show it:**
  - q07 asks about Sam Reed on 10 March at 00:00. The statement was made at 12:00 that day.
  - q08 asks about Pia Holm on 30 June. The statement was made on 1 July.
  - So both answers are UNKNOWN whether or not the claim is believed, and the configuration without a
    reviewer scores the same 13/15.
- **This is limitation 3 in the README.**

## D2: gold claims that did not reach memory (7 of 12)
| Message | Source text | Stage | Detail |
|---|---|---|---|
| h1-1 | "Welcome Jonas Berg, who joined Lumen Labs as CFO on 3 March 2025!" | 2 | in the domain; the leading "Welcome" defeats the pattern (reported as unparsed) |
| h2-1 | "Lena Fischer is the Product Lead at Orbit." | 2 | the "is <title> at" phrasing is missing from rules:v2 (6B known failure 2); not reported, because "is" is not a domain verb |
| h2-2 | "Lena Fischer's manager is Raj Patel." | 2 | possessive phrasing unsupported; not reported |
| h2-3 | "Update: Lena Fischer stopped reporting to Raj Patel in June." | 2 | the "Update:" prefix is unsupported (reported as unparsed) |
| h3-2 | "Kim lives in Lisbon." | 2 | a generic statement: outside rules:v2's domain by design |
| h3-3 | "Noah manages Kim." | 2 | inverse phrasing unsupported (reported as unparsed) |
| h3-4 | "She also mentors two interns." | 2 | a pronoun subject and a generic statement: outside the domain |

**Of the 5 that reached memory,** one has a temporal mismatch: h3-1, "Kim has worked at Vector since 2022."
- **What is stored:** held by 1 January 2023, start not stated.
- **What the gold says:** a start in 2022.
- **The stage:** 9, a convention difference. The Phase 2 gold encodes "since" as a start, and v2's formation
  maps "since" to a latest start only, deliberately (candidate-ir.md §5, `gupi.formation.validate.valid_time`, and the "since" known issue).
  It is not stage 3: the extractor's reading is the documented one.

**Stages 4 to 8 do not occur in D2.** Every candidate was formed, stored with the valid time its candidate
maps to, and believed.

## D3 (implementer-written): expected candidates not formed (11 of 31)
| Outcome | Count | Passages |
|---|---|---|
| absent: pronoun subject (stage 2) | 1 | p32 |
| withheld by design (stage 4, correct behaviour) | 4 | plans p08, p09, p20; forwarded copy p12 |
| waiting for review (stage 4, correct behaviour) | 6 | hedged p07, p19; corrections p05, p25; unread time p03, p28 |

**Why these are not errors:** in the D3 expectations, these are the intended outcomes. The stored
candidates keep the evidence, so a reviewer can still form them.

## D5 and D6: the GUPI structured arm
| Question set | Questions | Earliest stage | Gold-turn states (counted once per question) |
|---|---|---|---|
| LoCoMo held-out | 1,676 | 2 (no candidate from any gold turn) for all | 2,187 outside the extractor's domain, 238 in the domain but not parsed |
| LongMemEval subset | 63 (with gold turns) | 2 for all | 101 outside the domain, 13 not parsed |

**What this means:**
- **No retrieval failure exists to attribute.** Nothing was stored, so stages 3 to 8 cannot occur.
- **The text retrievers' misses stay with them:**
  - **What they are:** cases where the evidence was in the text and was not ranked high enough.
  - **Why they are not reassigned to GUPI:** GUPI never had that evidence to retrieve.
- **On LongMemEval, a second barrier remains:**
  - **The barrier:** the structured retriever needs a named entity, and the questions ask about "I" and
    "my".
  - **The consequence:** even perfect extraction would leave most questions without a structural handle.
    This is Phase 5's finding, unchanged.

## Unresolved evaluation disagreements (gold not changed)
- **Two D1 gold answers (q01, q03)** reason as v1 did, as documented in Phase 4 v2. They are unresolved
  disagreements, not proven gold errors (see above).
- **The Phase 2 gold encodes "since X" as a start,** which disagrees with the deliberate "since" reading.
  This is also unresolved: both readings are defensible.
- **No D1 question covers the periods of w2-1 and w2-3,** so the frozen questions cannot detect the
  difference between policy formation and the recorded review decisions.
