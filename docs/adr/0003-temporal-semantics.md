# ADR 0003: Bitemporal semantics

Status: accepted (revised before Phase 1), 2026-11-02

## Times GUPI keeps
| Time | Where | Meaning | Set by |
|---|---|---|---|
| valid time | claim bounds | when the claim says the proposition is true | the source / extractor |
| `occurred-at-earliest/-latest` | `event` claims | when an event happened | the source / extractor |
| `observed-at` | observation | when the source produced the statement | the source |
| `received-at` | observation | when GUPI ingested it | GUPI's clock |
| `recorded-at` | claims, reviews, supersessions, alternatives | transaction time | GUPI's clock |

Callers can never supply `recorded-at` or `received-at`, and a decision whose clock reading is earlier than
the history it builds on is refused, so "what GUPI believed in March" cannot be rewritten later.

## Valid time
- A claim holds on a **half-open** interval `[start, end)`.
- Each boundary lies in a window `[earliest, latest)`: `valid-from-earliest/-latest`,
  `valid-to-earliest/-latest`. Exact: earliest == latest. "June 2025": 2025-06-01 .. 2025-07-01.
  A missing bound is unbounded on that side. Nothing is invented to fill it.
- No end bounds = **end unknown**, never "still true".
- "Still the case" in a source = `valid-to-earliest` = that observation's `observed-at`
  (`valid-to-basis "ongoing-at-observation"`): true up to then, nothing known after.
- Per claim, `holds_at` is three-valued: TRUE, FALSE, UNKNOWN.

## Transaction time and status
Claims are never mutated. Reviews are events: the **latest review recorded by t** sets the status at t,
so a claim rejected in May and re-accepted in July is believed again from July. If an acceptance and a
rejection or retraction share a timestamp, the claim is not believed. A supersession recorded by t
overrides reviews. `status.status_at` (Python) and `believed_at` (TypeQL) implement the same rule, and
tests check they agree.

## Answers
`Memory.ask(type, roles, valid_at, believed_at)` combines the claims about one proposition:

| Answer | Meaning |
|---|---|
| TRUE / FALSE | a claim believed at t says it did / did not hold at v |
| UNKNOWN | claims had been recorded by t, but none believed decides v (bounds uncertain, or only hypotheses / rejected / retracted claims) |
| NOT_YET_KNOWN | nothing about the proposition had been recorded by t |
| CONTESTED | believed claims disagree (some TRUE, some FALSE) |

Absence of a claim is never FALSE: GUPI does not assume a closed world.
Tests: `tests/unit/test_temporal.py`, `tests/integration/test_temporal_queries.py`.

## Open questions (Phase 3)
- A persistence default ("assume a job continues unless contradicted") would turn some UNKNOWNs into
  presumptions; if added, answers must label it as a presumption.
- Supersessions cannot yet be reversed.
- Valid-time evaluation runs in Python over the claims for one proposition; moving the certain cases into
  TypeQL functions would let TypeDB narrow candidates for broad questions.
