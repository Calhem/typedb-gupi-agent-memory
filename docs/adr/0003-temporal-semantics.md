# ADR 0003: Bitemporal semantics

Status: proposed (Phase 0), 2026-11-02

## Times GUPI keeps
| Time | Where | Meaning |
|---|---|---|
| valid time | `fact` bounds | when the fact is true in the world |
| `occurred-at-earliest/-latest` | `event` (a `fact` subtype) | when an event happened |
| `observed-at` | `observation` | when the source produced the statement (e.g. message timestamp) |
| `received-at` | `observation` | when GUPI ingested it |
| `recorded-at` | facts, reviews, supersessions | transaction time: when GUPI recorded that belief or decision |

Observation time and asserted time are separate: a note written in November can say something about June.

## Valid time
- A fact holds on a **half-open** interval `[start, end)`.
- Each boundary is only known to lie in a window `[earliest, latest)`:
  `valid-from-earliest`, `valid-from-latest`, `valid-to-earliest`, `valid-to-latest`.
  - Exact date: earliest == latest.
  - "June 2025": earliest 2025-06-01, latest 2025-07-01 (`time-precision "month"`).
  - Unknown: the bound is absent. Nothing is ever invented to fill it.
- No end bounds = **end unknown**. It does not mean "still true".
- "Still the case" in a source = `valid-to-earliest` set to that observation's `observed-at`
  (`valid-to-basis "ongoing-at-observation"`). It proves the fact held until then, nothing after.
- `holds_at(fact, t)` is three-valued: TRUE, FALSE, UNKNOWN (`gupi/temporal.py`).
- All times are `datetime-tz`, stored in UTC.

## Transaction time
Facts are never mutated or deleted by normal operation. Corrections add a new fact plus a
`supersession`; acceptance, rejection and retraction add a `review`. Each has `recorded-at`.
`believed_at(t)` returns the facts accepted by `t` and not superseded, rejected or retracted by `t`.

So two different questions both work (verified in `tests/integration/test_core_ontology.py`):
- What do we *now* believe was true in August 2025? (`believed_at(now)` then `holds_at(..., Aug)`)
- What did we believe *in March 2025* about August? (`believed_at(March)` then `holds_at(..., Aug)`)

## Open questions (for Phase 3)
- A persistence default ("assume a job continues for N months unless contradicted") would turn some
  UNKNOWNs into presumptions. If added, it must be labelled as a presumption in answers.
- Re-acceptance after rejection: `believed_at` currently lets any rejection recorded by `t` win.
- Valid-time filtering happens in Python in Phase 0; Phase 3 should move the certain TRUE/FALSE cases
  into TypeQL functions to narrow candidates on the server.
