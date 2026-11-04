# Phase 7B Stage 2B: evidence integrity and candidate format 1.1

Date: 2026-11-04.
- **Branch:** `feature/phase-7b-evidence-integrity`, from main `3d8cc72` (Stage 2A merged). **Not merged.**
- **Environment:** TypeDB 3.14.1 (Docker, local).
- **Nothing external:** no API call, model inference or model download.
- **Spending:** $0.
- **Unchanged:** the default extractor, the specialist branch, and the frozen inputs and gold.

## What was done
| Item | Result | Document |
|---|---|---|
| Candidate format 1.1 | additive: optional `asserted_by_kind`, and a null target for corrects / retracts / updates. 1.0 ids and payloads are unchanged, and **no schema migration** is needed | [candidate-format-1.1.md](candidate-format-1.1.md) |
| C2 claimant kinds | person / organisation / unknown are persisted as person / organization / unclassified. An absent kind is never treated as a person. 11 of 12 cases pass; 1 is a strict expected failure (S8: same-named people in one conversation) | [claimant-classification.md](claimant-classification.md) |
| D3 correction targets | null targets reach review and are never resolved automatically. No target is invented and nothing is superseded. `store.assign_correction_target` records a reviewer's choice, append-only | [correction-targets.md](correction-targets.md) |
| F1 forwarded copies | a copy of a forwarded copy is withheld. Independent assertions stay distinct, and the independent count follows originators | [forwarded-attestations.md](forwarded-attestations.md) |
| Inferred statements | policy kept: formation now sends any `basis: inferred` candidate to review. The offline interface still defers a model's inferred assertion. No new inference | [remaining-limitations.md](remaining-limitations.md) (L5) |
| Offline interface | it is now `model:candidate-v1.1`. It emits format 1.1 and reads response formats `/1` (every recorded fixture) and `/1.1` | below |
| Regressions and Phase 6D | identical to the committed results; Phase 6D on manifest v3 is identical to first-run, apart from known timing fields | [compatibility-results.md](compatibility-results.md) |

## The offline interface (changes from offline-extractor-interface.md, which describes v1 as built in Stage 2A)
| Item | v1 (Stage 2A) | v1.1 (Stage 2B) |
|---|---|---|
| method | `model:candidate-v1` | `model:candidate-v1.1` |
| response formats read | `gupi.model-response/1` | `/1` and `/1.1`. The kind vocabulary is `organization`, `unclassified` in /1 and `organisation`, `unknown` in /1.1 |
| candidate format | `gupi.candidate/1` | `gupi.candidate/1.1` |
| organisational or unknown claimant | `claimant-kind-not-representable` (no candidate) | a candidate with `asserted_by_kind`. A forward header's sender is `unknown` |
| unmatched correction / retraction / update | `correction-target-unresolved` (no candidate) | a null-target candidate, flagged `correction-target-unresolved`, which formation reviews. `contradicts` still gives the outcome |

## Tests
| Point | Result |
|---|---|
| start (`3d8cc72`) | 467 passed, 20 expected failures (measured on main before the merge) |
| end (`e034b52` plus docs) | **513 passed, 19 expected failures** |

**The expected failures:**
- **Retired:** the two Stage 2A C2 demonstrations. They are now real tests.
- **Added:** S8 (strict).
- **Unchanged:** the 18 `rules:v2` D1/D2 demonstrations.

**New tests:**
- format 1.1: 13
- C2: 12
- D3: 13, plus 1 interface test for the pronoun case
- F1: 10
- the interface: updated for 1.1, with a format test

**The failures before each fix** are in [before/](before/).

## Reproduction
    uv run pytest -q
    uv run python -I -m gupi.benchmarks.phase7b.harness tests/fixtures/phase7b-dev/offline \
        --responses tests/fixtures/phase7b-dev/offline/responses.json --formation --json /tmp/run.json
    uv run python -I -m gupi.benchmarks.diagnosis.versions --json /tmp/versions.json
    uv run python -I -m gupi.benchmarks.e2e --label <new-label> --parts all --manifest docs/evaluation/phase-6d/manifest-v3.json
    uv run python -I -m gupi.benchmarks.e2e.compare first-run <new-label>

## Files
| File | Contents |
|---|---|
| candidate-format-1.1.md | the specification and the compatibility rules |
| claimant-classification.md | C2 |
| correction-targets.md | D3 |
| forwarded-attestations.md | F1 |
| compatibility-results.md | format 1.0 compatibility, the regression runs, Phase 6D v3, the developer-fixture harness |
| remaining-limitations.md | what is left, and why |
| dev-harness-run.json | the raw harness run |
| before/ | the test failures recorded before each fix |
