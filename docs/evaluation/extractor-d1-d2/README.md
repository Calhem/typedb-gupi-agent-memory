# D1/D2 extraction correctness milestone: before and after

Date: 2026-11-04. Branch `feature/extractor-d1-d2-correctness`, from `main` at `29732f9`. TypeDB 3.14.1.
No API calls, and no models downloaded. Version selection and behaviour: docs/formation/rules-v2.1.md.

## Regression tests and the original failures
**Where the tests are:**
- `tests/unit/test_formation_rules_v21.py`: 51 tests, plus 18 strict expected failures.
- `tests/integration/test_rules_v21_store.py`: 2 tests.

**How the defects were shown:**
- **Original failures:** before the corrections existed, the unit tests were run with `rules:v2.1` defined as
  a stub, a subclass of `rules:v2` that changed only its name.
  - **What failed:** 19 tests.
  - **The detail:** [original-failures.txt](original-failures.txt) lists them: every D1 pronoun case, "They
    joined", "I" with no author, and every D2 expression.
- **The same checks against `rules:v2`:** they run as strict expected failures for each case it gets wrong.
  So every test run proves `rules:v2` still has both defects, which is required for reproducibility. The
  integration test shows `rules:v2` still forms a believed claim about "She".

**Added during the milestone, each failing first:**
- **Three more D2 expressions:** "lost my job", "got a temp job" and "accepted for an internship", from the
  Phase 7A sample.
- **A test against an over-report:** a pronoun speaker with no domain content must not be reported as an
  unresolved reference.
  - **Why it was needed:** the first version of the correction over-reported it.
  - **How it was found:** a comparison run, which labelled 456 LongMemEval clauses "unresolved reference"
    merely because a pronoun reported the speech.
  - **What happened:** it was corrected before anything was committed, and only the corrected run is kept.

## Before and after (comparison.json, from `python -m gupi.benchmarks.diagnosis.versions`)
| Check | rules:v2 | rules:v2.1 | Same? |
|---|---|---|---|
| Frozen 6B set (32 passages): precision, recall, every field | 30/30, 30/31 | 30/30, 30/31 | **identical** (candidates and formation decisions also identical, by test) |
| Phase 2 conversations, held-out / development | 5/12, 8/12 | 5/12, 8/12 | **identical** |
| Phase 6C adversarial cases, through the store (17) | 17/17 on every measure, 0 unsupported definitive | the same | **identical** |
| Phase 4 world end to end through the store (6D gupi-e2e) | 13/15 | 13/15 | **identical** answers |
| Phase 4 answers, v1 and v2 (gold claims and rules:v1; no rules:v2.x involved) | v1 15/15, v2 13/15 | — | identical to the committed `retrieval-v1.json` / `retrieval-v2.json` |
| Phase 7A probes v1: candidates changed | — | p1-20, p1-21, p1-22, p3-07: the "She" candidates are gone | the only changes |
| Phase 7A probes (v1 + v2): rejection reasons changed | — | 13 probes | reporting only |
| LoCoMo, complete (5,882 turns): candidates | 0 | 0 | same |
| LoCoMo rejections by kind | no-pattern 536 | no-pattern 536, unsupported-expression 8 | 8 newly reported |
| LongMemEval S, complete (246,750 turns): candidates | 0 | 0 | same |
| LongMemEval rejections by kind | no-pattern 74,788 | no-pattern 74,758, unsupported-expression 228 | 228 named (30 were reported generically before, 198 were silent) |
| Phase 7A sample (100 turns) rejections | no-pattern only | LoCoMo targeted: 4 unsupported-expression | 4 named |

**The phrasings reported as unsupported on the complete datasets:**
- **LoCoMo:** "lost my job" (6), "accepted for an internship" (1), "got a temp job" (1).
- **LongMemEval's most frequent:** "was appointed", "your boss", "my boss", "began working", and other
  forms of "appointed".

**No unresolved references occur in either dataset.** Their pronoun sentences never matched a pattern,
which is why D1 was invisible there.

## Full test results
This milestone ends with the whole suite passing against TypeDB 3.14.1 (see the final report): the 356
earlier tests plus the new ones, and the strict expected failures.

## Remaining known limitations
- **No coreference:** pronoun-carried facts are now rejected. That is safer, but it loses recall.
- **D2 expressions:**
  - **What the list is:** fixed and diagnostic.
  - **What it over-reports:** some reported "appointed" and "boss" uses are not employment facts about a
    participant (institutional appointments, advice text).
  - **What it misses:** expressions not in the list stay unreported.
- **Lowercase pronouns** are unchanged.
- **The domain and phrasing limits** of Phase 7A are untouched: this milestone adds no patterns.
- **No caller was switched to `rules:v2.1`.** Choosing a default is left for review.
