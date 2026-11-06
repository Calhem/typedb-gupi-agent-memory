# Phase 8D: governed memory foundations

**Development data, manual extraction, inside the subscription. No paid calls. Not a benchmark or leaderboard result.** Results:
[8d-manual-dev.json](results/8d-manual-dev.json). Design: [conversational memory](conversational-memory-design.md). Protocol:
[evaluation](evaluation-protocol.md). Decision record: [ADR 0010](../../adr/0010-events.md).

## P2: stated relationships
**Built.** "My sister Kate" now gives an `author —sister→ Kate` statement; "My manager Alice" gives a typed `reporting` claim. Code checks the grammar: known
author, own direct unquoted words, a noun from a closed list, a capitalised name. A manager's facts can now travel: *Juno → Alice → Meridian*.

**Still stopped:** a bare "my sister", "my former manager", "my late husband", someone else's "my", forwarded text, a pet, and anything where the words and the
reply disagree. "My sister, Kate" goes to review. One name with two different relations in a conversation goes to review, not merged.

**Named people are never merged.** A speaker called Kate and "my sister Kate" stay separate. The same name across sessions stays two referents, with at
most a hypothesis.

**On real data: no effect.** The pattern occurs **zero times** in 788 development turns.

## P4: dated events
**Built.** Moves, projects, purchases, acquisitions and other happenings form as `event-statement`, with their own window. `Memory.events` reads a timeline.

| Requirement | How it holds | Test |
|---|---|---|
| Reuse the event type | fills the `event` slot `core/0001` left abstract | |
| Event time is not assertion time | occurrence window, separate from the observation | `test_event_time_is_not_assertion_time` |
| Explicit versus inferred | `stated` or `derived` | `test_a_derived_date_says_so` |
| No invented dates | no date stays none; unreadable goes to review | `test_a_missing_date_stays_missing` |
| No invented participants | a missing subject stops | `test_an_implicit_participant_is_not_invented` |
| No continuing relationships | no valid time; `ask` refuses it; a join event gives no employment | `test_joining_as_an_event_implies_no_continuing_employment` |
| Corrections | review, then supersession, with history intact | `test_a_correction_waits_for_review…` |
| Disputes | both kept, flagged, neither preferred | `test_disputed_dates_are_both_kept_and_flagged` |
| Retractions | noted while pending, and nothing changes | `test_a_pending_retraction_marks_the_event…` |
| Spells unchanged | same answers with events present | `test_events_leave_spells_exactly_as_they_were` |

**Boundary:** joining or leaving an employer stays employment `start` or `end`, so spells keep working.

**Also stopped:** a state ("was CTO"), a span, a second date, and anything in the future. A word list decides what's a state, so some genuine events are stopped: "had
an interview" is one.

## Schema and temporal compatibility
| Item | Change |
|---|---|
| Migration | `core/0013`: one relation type, one attribute. Additive; tested on a populated database, and every claim reads back identical |
| P2 | no schema change |
| Response format | 1.2 adds `event`; 1.1 cannot introduce one |
| Unchanged files | `answering_v2.py`, `temporal.py`, `timeexpr.py`, `qualification.py` |
| Regressions | Stage 3B's replies are identical by hash; all 8B development rankings identical; 18 of 18 fixture checks |

## Does this increase useful connectivity?
**Dates, yes. Connections, no.**
| Development conversations | Phase 8C | Phase 8D |
|---|---:|---:|
| Claims formed | 123 | 133 |
| Dated events | 0 | 20 |
| Dated events withheld | 22 | 0 |
| Held for review | 12 | 22 |
| Claims linking two named things | 5 (4.1%) | **5 (3.8%)** |
| Turns with a claim | 14.1% | 15.1% |
| Gold turns with a claim | 42 of 117 | 47 of 117 |

| Multi-hop (38), C over B, points | R@5 | R@10 | R@100 |
|---|---:|---:|---:|
| Phase 8C | +0.2 | +1.7 | +0.7 |
| Phase 8D | −0.4 | +1.7 | +0.7 |

Temporal recall is unchanged, with C equal to B. Integrity: 0 severe findings. That was expected: an event adds a date to a turn that keyword search could already find.

**What the events may offer is answers, not recall.** For 15 of 63 temporal questions, every gold turn now has a dated event. Whether a timeline answers them is untested.

**Two limits:**
- All 20 dates are `derived`, because chat says "last week". They rest on the message date.
- 10 of the extra review items are events with dates the reader can't parse. "Last Friday" is the commonest, with 9 cases of that shape among all time phrases. A small `timeexpr`
  extension would recover most, and isn't in this phase.

## Limits
Extraction was re-marked by the builder, who knew the parser and the aggregate 8C results, though no questions. It's not independently verified. Development
conversations have few named third parties, so P2 and session identity are tested on invented data only.
