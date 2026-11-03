# `rules:v2`: the offline candidate extractor (Phase 6B)

Date: 2026-11-03.
- **Code:** `gupi.formation.rules_v2`.
- **Tests:** `tests/unit/test_formation_rules_v2.py`.
- **Evaluation:** docs/evaluation/phase-6b-extraction.md.

It emits `gupi.candidate/1` sets. It writes nothing to memory or TypeDB. `rules:v1` is unchanged and stays
the default.

## Scope (deliberately narrow)
- **Domain:** employment (an employee person and an employer organisation, optionally a job title) and
  reporting (a report and a manager).
- **Units:** one sentence at a time, at most two clauses joined by "and". The second clause may reuse the
  first clause's subject.
- **Names:** one or two capitalised words. "I" is accepted only when the observation's author is known.

| Phrasing | Candidate |
|---|---|
| "joined / started at / was hired by X (as T) (in M)", "was promoted to T at X (in M)", "Y, who joined X in M, ..." | employment, `start` |
| "left X (in M)" | employment, `end` |
| "has worked / been at X since M", "Since M, Y works at X" | employment, `holds-since` + `holds-at` (observation) |
| "works / is working at X", with "still", "now", "probably" | employment, `holds-at` (observation) |
| "will / might / may / could / plans to / is expected to join X", "is joining X"; "is leaving / will leave X" | `planned` start or end, with the modal's commitment |
| "no longer works at X", "doesn't work at X", "isn't with X (any more)" | employment, **negative** `holds-at` |
| "stopped reporting to Z (in M)" / "has reported to Z since M" / "reports to Z" / "doesn't report to Z" | reporting: end / holds-since / holds-at / negative |
| leading "From M, ..." | `start` |

## Cues it records
| Cue | Recorded as |
|---|---|
| "Correction:", "Correction to ...:" | a `corrects` relation to the latest earlier candidate (same proposition, same boundary) in this or an earlier set of the thread; **never an overwrite**. Without one, no relation, and a note. |
| "X told me (that)", "X says / said / wrote", "According to X," | attribution `reported`, asserted by X, via the author |
| "Reportedly", "I hear(d) that", "Word is" | attribution `rumour`, commitment `unknown` |
| "I think", "I believe", "Probably", "Apparently" / "Maybe", "Perhaps", "Possibly" | commitment `probable` / `possible` |
| a "---- Forwarded message ----" block, with an optional "From:" line | attribution `forwarded`, asserted by the sender, transmission `forwarded`. A copy of a statement made earlier in the same set gets a `repeats` relation, so it is not independent corroboration. |

**Confidence** is always `None`, because a rule extractor has no calibrated confidence. **Commitment** is the
source's. **Acceptance** is not part of a candidate at all.

## Known limits
It does not handle:
- pronouns other than the author's "I"
- implied employers ("He rejoined in June")
- more than two clauses
- dates it cannot read: "next month" and seasons are kept as written, without a window
- negations other than the listed forms
- corrections to an existing claim, which would need a memory lookup (6C)

A domain verb with no supported pattern is reported as rejected, with a reason.
