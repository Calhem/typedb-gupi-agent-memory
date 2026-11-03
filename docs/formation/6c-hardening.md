# Phase 6C hardening: evidence integrity through to the answer

Date: 2026-11-03. Findings: 6c-hardening-audit.md.

## Three separate dimensions
A v2 answer now reports three things. None of them is folded into another.

| Dimension | Values | Where |
|---|---|---|
| **Temporal status** | TRUE, FALSE, PRESUMED, UNKNOWN, CONTESTED, NOT_YET_KNOWN (the v2 classifier; **unchanged**) | `AnswerResult.answer`, `Result.answer`, `Binding.answer` |
| **Evidential standing** | `direct`, `qualified`, `unrecorded`, `n/a`, with qualifiers, originators and the count of independent originators | `.qualification` (v2 only) |
| **Acceptance** | who admitted each deciding claim into memory (the policy `formation:v1`, or a named reviewer) | `.qualification.accepted_by`; each claim's reviews |

## Evidential standing (`gupi.qualification`)
It is computed only from the claims that decided the answer (the v2 basis), and only from what they record
(core/0011). There are no confidence scores and no ranking of sources.

**Qualifiers on each claim:**
- `hedged:<commitment>`: the source hedged
- `reported`, `quoted`, `forwarded`, `rumour`, `unattributed`: how the assertion reached the source
- `provenance-not-recorded`: a claim recorded before formation provenance existed

**Standing:**
- **`direct`:** at least one deciding claim has no qualifier.
- **`qualified`:** every deciding claim is hedged, reported, forwarded or rumoured.
- **`unrecorded`:** every deciding claim predates formation provenance. Such claims are answered exactly as
  before.
- **`n/a`:** no claim decides the answer (UNKNOWN, NOT_YET_KNOWN).

**`definitive`** is true only for a TRUE or FALSE whose standing is `direct` or `unrecorded`. A TRUE or FALSE
resting only on qualified evidence is flagged as not definitive, and its explanation says so. CONTESTED and
PRESUMED are never definitive.

**Independence** counts distinct originators:
- the claim's asserter if recorded, otherwise the observation's author
- an unknown originator counts once per source

Forwarding and repetition never add an originator.

**Acceptance is not verification.** Every explanation that names an acceptance says "admission is not
verification".

## Unchanged
- The v2 classifier and every status label.
- v1, which carries no qualification. It remains the legacy default, and its answers are not qualified
  (audit H8).
