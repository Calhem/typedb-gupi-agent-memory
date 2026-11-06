# Phase 8F.3: apparent contradictions with no stated transition

**Design only. Production spell semantics are unchanged.** All examples are invented.

## The gap
`classify` compares evidence at one instant. If "she works at Acme" was said in March and "she doesn't work at Acme" in June, each is correct at its own moment: TRUE in March and FALSE in June. Nothing says *contested*, because no single instant has both. That's right as far as it goes. But a reader sees a story the evidence never told: she left, with no one saying so. If "she works at Acme" appears again in September, she seems to have left and returned.

## Five things that look alike
| Kind | Example | What is really going on | What GUPI does today | What should happen |
|---|---|---|---|---|
| **1. A genuine change** | "Joined Acme in 2020." "Left in 2022." | a stated transition | correct: spell, then termination | nothing new |
| **2. Conflict about the same time** | one source says she was there in March, another says she wasn't | two claims cover one instant | correct: CONTESTED where they overlap | nothing new |
| **3. Different aspects** | "I have a bakery." "The bakery hasn't opened." | owning it and trading are different propositions | **looks like a flip** if they share a label | separate the propositions; a reader, not code, can see this |
| **4. Retrospective correction** | "Actually, I never worked there." | the earlier statement is withdrawn | correct if marked: review, then supersession | nothing new |
| **5. Missing transition** | "Works at Acme" (March), "doesn't work at Acme" (June) | it probably changed, unrecorded | **silently flips** | **say that a change is implied and unrecorded** |

Kinds 1, 2 and 4 are already handled. **The gap is 3 and 5, and they can't be told apart from the words alone.**

## Direction matters
| Sequence | Reading | |
|---|---|---|
| not yet, then yes | forward: the transition was just never mentioned | ordinary |
| yes, then not | either a change or a conflict | needs flagging |
| yes, then not, then yes | either two unrecorded changes, or an underlying conflict | flag strongly |

Some states can only go one way. A bakery that has opened may close, but "hasn't opened yet" after "has opened" is impossible. A degree, once finished, can't be unfinished. **Telling these apart needs knowledge of the state**, which GUPI doesn't have.

## Can a general check be safe?
**Yes, if it only adds a note, and no, if it changes an answer.**

**Proposed rule:** over one proposition (claim key and predicate, since statements share a key across predicates), order the believed positive and negative evidence by valid time. Where a positive and a negative are adjacent with **no stated start or end between them, and no supersession**, report `unexplained change` on that pair.

| Requirement | How it holds |
|---|---|
| Never changes `classify` | a separate step over the same claims, after the answer |
| Never picks a side | both statements are named; the answer stays as it was |
| Never invents a transition | it reports the absence of one; no boundary is created |
| Never treats silence as evidence | it needs an actual negative statement |
| Scoped | one proposition, so it cannot cross identities or activities |

**Where it surfaces:** as a qualification on the answer and on retrieved items, and in the review queue. It would not be a new `Answer` value.

| State | Safe? | Note |
|---|---|---|
| **Employment** | yes | reversible; adjacent flips are usually kind 5 |
| **Reporting lines** | yes | reversible |
| **Generic statements** | **only with the predicate in the key** | otherwise unrelated statements collide; negation and paraphrase will miss many |
| **Projects** | **only after activity identity** | relies on the same grouping Phase 8F is testing |
| **Events** | not applicable | an event doesn't hold, so it can't flip. Conflicting dates are already disputes |

## What it can't do
- **It can't see kind 3.** Different aspects need different propositions, which means a human or model split them first. A flag can only prompt someone to look.
- **It only finds explicit negatives.** "It hasn't opened" is a negative only if extraction records it as one, which needs polarity, or a role like `negated`.
- **It can't rank.** It says something needs explaining, not which statement is right.
- **False alarms.** A real change, simply unmentioned, is flagged. That's acceptable: the note is true, since the transition is unrecorded.

## Recommendation
Build it as a small, separate, additive qualification, first for employment and reporting, where propositions are clean. It's useful whether or not activities go ahead. This needs separate approval, and it doesn't touch spell semantics.

## What the Phase 8F ledgers showed
*Added after the readers finished. Everything above was drafted before any ledger was read, and it was wrong in one important way.*

| Finding | Detail |
|---|---|
| **Readers find contradictions well** | every ledger reported the central contradiction, unprompted and blind |
| **The proposed check finds nothing on their ledgers** | it needs explicit negatives. **No new ledger used the `negated` role once.** On those three it reports 0; only my own ledger gives it anything to work with |
| **None was a same-instant conflict** | none of the reported cases is one `classify` would call contested |
| **Reports were mostly real** | of 13 reports across three ledgers, 1 was a false alarm: a plan that came true on time, read as a conflict |

**Reported cases, by this design's kinds, classified by me and not independently checked:**
| Kind | Reports | |
|---|---:|---|
| 3 or 5: aspects, or a missing transition, on the central project | 6 | |
| 3: one thing or two (not truly a contradiction; an identity question) | 3 | |
| 5: past tense, then present tense, about a practice | 1 | |
| 5: a stated plan overtaken by a later circumstance | 1 | |
| Duplicate of the central case, under a related activity | 1 | |
| False alarm | 1 | |

**What changes.** The rule above is still safe, but it's nearly useless on its own, because it depends on negatives that extraction doesn't record. **The useful signal came from models reading a whole conversation, not from code comparing states.** So the better design has two parts:
1. **Detection by reading.** Consolidation reports apparent conflicts, each quoted and validated, as review items, and never as facts.
2. **The code check stays as a small backstop,** for clean states such as employment, once polarity is captured.

**Neither changes an answer, and neither touches spell semantics.**
