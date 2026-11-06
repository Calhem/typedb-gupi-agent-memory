# ADR 0010: an event happens; it does not hold

**Status:** implemented on the Phase 8D branch, awaiting review.

**Context.** Every dated happening was withheld: "ran a race last week" reads as `holds-at` over a window, and a valid time
can't say "at some instant in this window". Reading it as a `start` would turn a moment into a continuing state.

**Decision.** Migration `core/0013` adds `event-statement` under the abstract `event` the schema already had, and
`occurred-at-basis`. An event has an occurrence window and no valid time.
- **Time:** occurrence is separate from when it was said (the observation), and from when GUPI learned it (recorded-at).
- **No continuity:** it is never in spell assembly. `Memory.ask` and `Question` refuse it. In path overlap a state may be asked
  about an event's time, and an event is never asked whether it held.
- **Dates:** `stated` or `derived`. No date means no date. An unreadable date goes to review.
- **Not events:** states, spans, anything dated after the message.
- **Employment is unchanged:** joining or leaving an employer stays an employment `start` or `end`, so spells keep working. A join
  recorded as an event implies nothing about employment.

**Consequences.** Additive: no claim, id or proposition key changes. Corrections, disputes and retractions use the existing paths.
`Memory.events` reads a timeline, and reports different dates as disputed without choosing one.
