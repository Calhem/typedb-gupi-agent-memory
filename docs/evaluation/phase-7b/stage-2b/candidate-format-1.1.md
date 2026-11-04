# Candidate format `gupi.candidate/1.1` (specification and compatibility)

**What it is:** the minimum additive change over `gupi.candidate/1` (now called 1.0) needed for C2 and D3.
F1 needs no format change: it is a formation fix.

**What the audit read:**
- `gupi/formation/candidate.py`, `validate.py`, `form.py` (`_claim`, `decide`, `_existing_copies`,
  `_suggest_corrections`), `store.py`
- `gupi/qualification.py`, `gupi/memory.py` (`_ingest_claim`)
- schema `core/0003`, `0011`, `0012`, `people/0001`
- the offline interface `gupi/formation/model_candidate.py`

## What 1.0 has, and what 1.1 adds
| Field | 1.0 | 1.1 |
|---|---|---|
| `ir_version` (set) | `"gupi.candidate/1"` | `"gupi.candidate/1"` **or** `"gupi.candidate/1.1"`; the 1.1 fields below are allowed **only** in a 1.1 set |
| `attribution.asserted_by` | a surface (or a referent id, per the docstring; never honoured) | unchanged; in 1.1 it must occur exactly in the observation's text |
| `attribution.asserted_by_kind` | — | **new, optional**: `person`, `organisation`, `unknown`. Only with `asserted_by`. Omitted when absent |
| `relations[].target` | a candidate id in the set, or a `claim:` / `candidate:` id (required) | also **`null`**, for kinds `corrects`, `retracts`, `updates` only: "the source states a correction or retraction, but its target is not established" |

**What does not change:** every other field, and every enum.

## Compatibility rules
1. **Candidate ids are unchanged for 1.0 candidates.**
   - **Why:** `asserted_by_kind` enters the id computation (`_plain`) only when it is set, and a null target
     never occurs in 1.0.
   - **So:** the same 1.0 candidate has the same id before and after this milestone.
2. **1.0 payloads stay readable.**
   - **Where they live:** stored candidates keep their payload and `ir-version` attribute.
   - **Reading them:** `from_dict` reads both versions, and the tamper check (recomputing the id) still holds.
3. **No migration is needed.**
   - **Claimant kinds:** the schema already has the referent kinds needed: `person`, `organization`, and
     `unclassified` (people/0001, core/0003).
   - **Asserters:** `assertion:asserter` is played by any referent (core/0011).
   - **Versions:** `ir-version` is a free string (core/0012).
   - **Corrections:** an unresolved correction's suggestion uses the existing `target-resolution` values.
4. **Absence is not evidence:**
   - **The rule:** a 1.0 candidate (or a 1.1 candidate without `asserted_by_kind`) with an `asserted_by` has a
     claimant of **unestablished kind**.
   - **How it is persisted:** as an `unclassified` referent, never as a person.
   - **A behaviour change:** this changes how claims formed *from now on* from rules:v2 and rules:v2.1 reported
     speech are stored. Their claimants were previously created as people. claimant-classification.md
     reports it. Already-persisted claims are untouched.
5. **The extractors are unchanged.** `rules:v2`, `rules:v2.1` and the registry stay as they are, and both
   still emit 1.0. The default extractor is unchanged.
6. **Mapping kinds onto referents:** `person` → `person`, `organisation` → `organization`, and `unknown` or
   absent → `unclassified`.
   - **The spelling:** the format uses the British spelling the owner specified, and the schema keeps its
     existing label.

## Validation rules (deterministic)
| Rule | Issue code |
|---|---|
| `ir_version` is 1.0 or 1.1 | `version` |
| a 1.1 field in a 1.0 set | `version` |
| `asserted_by_kind` in {person, organisation, unknown} | `attribution` |
| `asserted_by_kind` without `asserted_by` | `attribution` |
| 1.1: `asserted_by` occurs in the observation text | `attribution` |
| `target = null` only for corrects, retracts and updates | `relation` |

## Formation (formation:v1 rules, unchanged in spirit)
- **Any stated correction, retraction or update goes to review.** That includes a null target, which is
  reviewed with the reason "its target is not established".
- **Nothing is superseded automatically.**
- **The suggestion** for a null target lists every plausible believed claim, but is never `resolved`:
  `missing` when there is none, `ambiguous` otherwise.
- **A reviewer assigns a target explicitly** with `store.assign_correction_target`.
  - **The record:** an auditable, append-only `correction-suggestion` that names the reviewer and the reason.
  - **The checks:** it refuses an unknown or no-longer-believed claim.
  - **What it does not do:** it supersedes nothing.
