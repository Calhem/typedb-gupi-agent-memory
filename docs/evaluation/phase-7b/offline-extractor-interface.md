# Offline extractor interface: `model:candidate-v1`

**What it is:** `gupi.formation.model_candidate.ModelCandidateV1`. It converts **recorded**, model-shaped
responses into `gupi.candidate/1` candidates.

**What it is not connected to:** it is connected to no model, API or local runtime, and it imports no
client.

**Versions:**

| Item | Version |
|---|---|
| response format | `gupi.model-response/1` |
| parser and extractor method | `model:candidate-v1` (a candidate set's `extractor` is `model:candidate-v1:<source>`, e.g. `:recorded`) |
| candidate contract | `gupi.candidate/1` (unchanged) |

```python
from gupi.formation.model_candidate import ModelCandidateV1
cset, report = ModelCandidateV1().extract(observation, prior=earlier_sets, schema=live_schema, response=recorded)
```

## The response format (`gupi.model-response/1`)
**The top level:** `{"format", "outcome", "assertions", "problems"}`.
- **`outcome`:** `assertions` or `no-relevant-assertion`.
- **Unknown fields** anywhere make the whole response invalid. That covers offsets, ids and dates.
- **Missing fields** do too: there are no defaults.

| Assertion field | Required | Values |
|---|---|---|
| `evidence` | yes | exact text from the message |
| `evidence_occurrence` | when the evidence occurs more than once | 1-based |
| `relation` | yes | `employment`, `reporting`, `statement` |
| `participants[]` | yes, at least 1 | `{role, text, kind (person / organization / unclassified), is_pronoun_or_vague}` |
| `times[]` | yes (may be empty) | `{text, kind (start / end / holds-since / holds-at)}`; **no dates** |
| `polarity`, `modality`, `commitment` | yes | the `gupi.candidate/1` enums |
| `attribution` | yes | `{mode, claimant (text or null), claimant_kind (required with a claimant), via []}` |
| `basis` | yes | `explicit`, `inferred` |
| `predicate` | statements | a few words |
| `object_text`, `title` | no | exact text |
| `correction` | no | `{kind (corrects / retracts / updates / contradicts), cue (exact text), earlier_statement}` |
| `allegation` | no | true or false |

**`problems[]`** is the model's own report: `{kind (unsupported-domain / ambiguous-reference /
insufficient-evidence), evidence, detail}`.

## What code does (never the model)
| Concern | Rule |
|---|---|
| Source grounding | `evidence` must occur exactly in the message. Several occurrences need a valid `evidence_occurrence`, otherwise `ambiguous-span`. Participants, times, title and object text must occur exactly, and exactly once, **inside** the evidence. The claimant and `via` must occur in the message. Otherwise `grounding-failure`. |
| Offsets | computed here from the located strings |
| Identity | never resolved. A pronoun (the rules:v2.1 list, or lowercase), or a participant the model marks `is_pronoun_or_vague`, gives `ambiguous-reference`. "I" needs a known author. |
| Time | read by `gupi.timeexpr` against the observation time. Unread phrases keep precision `unknown`, so formation sends them to review (flag `unreadable-time`). A present-tense verb (`reports`, `has worked`, …) in a `holds-at` holds at the observation time, as in rules:v2. "Since …" as a `start` is refused by validation. |
| Forwarding | text inside a forward marker is `forwarded` whatever the model says (flag `mode-forced-forwarded`). A claimant other than the header's sender is a `cue-conflict`. `forwarded` with no marker is kept, and flagged `forwarded-unmarked`. |
| Claimant kind | only a claimant stated to be a person yields a candidate. An organisation, an unknown kind, or a header sender of unstated kind gives `claimant-kind-not-representable` (C2, pending approval). |
| Polarity, modality, certainty | checked against the evidence, read from the start of its sentence. A negation with positive polarity, or a future or conditional with actual modality, gives `cue-conflict`. `certain` with a hedge or an allegation becomes `unknown` (flag `commitment-downgraded`), which formation sends to review. "…, not March" is a contrast, not a negation. |
| Corrections | the cue must occur. The target must be **exactly one** earlier candidate in the thread with the same type, participants and boundary. Otherwise `correction-target-unresolved` and no candidate (D3, pending the contract extension). |
| Inference | `basis: inferred` gives `inferred-not-admissible`. formation:v1 has no route to review for an inferred assertion, so none is admitted. |
| Validation | every candidate goes through `gupi.formation.validate` (with the schema the caller passes). Failures are reported as `validation`, apart from the extractor's own outcomes. |
| Formation | unchanged: `store.submit` applies formation:v1 to these candidates exactly as to rules candidates |

## Outcomes and flags
**Outcomes** are the extractor's, not formation's. They never produce a candidate:
- `no-relevant-assertion`
- `invalid-model-output`
- `grounding-failure`
- `ambiguous-span`
- `ambiguous-reference`
- `claimant-kind-not-representable`
- `correction-target-unresolved`
- `inferred-not-admissible`
- `cue-conflict`
- `unsupported-domain` and `insufficient-evidence`, both reported by the model
- `validation`

**Flags** are attached to a candidate that *was* produced:
- `unreadable-time`
- `commitment-downgraded`
- `mode-forced-forwarded`
- `forwarded-unmarked`
- `predicate-paraphrased`
- `allegation`

**Determinism:** the same response gives the same candidates (with the same ids), and the response is never
modified. This is covered by a test.

**Tests:**
- `tests/unit/test_model_candidate.py`: 23 tests.
- `tests/integration/test_model_candidate_store.py`: formation, and schema rejection.
