# Phase 6C adversarial evaluation (development-only), first run

Date: 2026-11-03. Reproduce:

    uv run python -I scripts/evaluate_adversarial.py --json docs/evaluation/phase-6c-adversarial-first-run.json

Raw results, with each case's expected values, actual values and explanation:
`phase-6c-adversarial-first-run.json`.

**Not independent or competitive evidence.**
- **Who wrote it:** the 17 cases (`tests/fixtures/formation/adversarial-v1.json`) were written by the
  implementer.
- **When:** they were frozen (`b510a32`) before the evidence qualification existed, but by the same person
  who then designed it, with the cases in mind.
- **So what it is:** a check that the intended behaviour holds end to end, from text to answer, through
  TypeDB. It does not estimate how GUPI handles evidence it was not designed for.

## Method
- Each case runs in its own disposable TypeDB 3.14.1 database.
- **The pipeline:** ingest the messages, extract them with `rules:v2`, form them with `formation:v1` (plus
  the case's reviewer approvals), then ask one question under v2.
- **The measures,** each scored separately:

| Measure | Correct when |
|---|---|
| temporal | the v2 answer equals the expected one |
| qualification | the evidential standing and the set of qualifiers both equal the expected ones |
| attribution | the known originators equal the expected ones |
| independence | the number of independent originators equals the expected one |
| citations | the cited messages equal the expected ones |
| unsupported definitive | `definitive` is true where the evidence does not warrant it |

## First-run results
| Measure | Result |
|---|---|
| temporal answer | **17/17** |
| evidence qualification | **17/17** |
| attribution | **17/17** |
| independence | **17/17** |
| citation support | **17/17** |
| unsupported definitive answers | **0/17** |
| definitive answers withheld where warranted | 0 of 7 |

## What the first run hides
- **Case a12 passes partly by default.** It covers a pending correction of an existing claim.
  - **Why:** its correction sentence, "Correction: Alice Grey has worked at Acme Labs since April 2025, not
    March.", is **not extracted at all**. The `rules:v2` "since" pattern does not allow a trailing
    ", not March".
  - **Worse,** the sentence was dropped **silently**, because "worked" was missing from the domain verbs used
    to report skipped sentences. That silence is fixed in `0d5cc4a`; the extraction gap is not (rules-v2.md,
    known limits).
  - **What still tests the review path:** the integration tests, with a supported phrasing.
- **Every case uses `rules:v2` phrasings,** in one domain. Anything the extractor does not recognise never
  reaches formation, so this evaluation cannot show how unrecognised evidence would be qualified.
- **The cases fix the qualification's definitions** (standing, qualifiers, originators), so agreement is
  expected by construction for those measures. The measures that depend on the rest of the pathway are
  temporal answers, citations, and false corroboration (a07). They pass because the pathway preserved
  provenance end to end.
