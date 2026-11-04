# Offline evaluation harness

**What it is:** `gupi.benchmarks.phase7b.harness`, scorer version `phase7b-scorer/1`. It compares
`rules:v2.1` with recorded `model:candidate-v1` outputs on any corpus in the annotation-template format, so
the independent corpus will run without changes to the scorer.

    uv run python -I -m gupi.benchmarks.phase7b.harness <folder> --responses <responses.json> [--gold <file>] [--formation] [--json <out>]

**Inputs:**
- **The corpus:** `<folder>/passages.csv`, and the gold (`assertions.csv`, or `--gold`, such as the
  adjudicated file). Both must pass `gupi.benchmarks.phase7b.annotations check`, or the run stops.
- **The responses:** `responses.json` holds `{"responses": {passage_id: response}}`, recorded responses only.

**Offline operation:**
- **No network:** no model, API client or network is used. A test blocks sockets during a run.
- **With `--formation`:** each system's candidates go through `store.submit` in a disposable **local** TypeDB
  database, the same formation as everywhere else.

**Observations:**
- **What one is:** each passage becomes one observation. Its source is `src:7b:<set>` and its record key is
  the passage id.
- **Its time:** the document date plus the turn, in minutes.
- **Its context:** the thread id, or else the passage id.
- **Its author:** the stated author.
- **Order:** threads are read in order, and earlier candidates in the thread are the `prior` for corrections.

## What is recorded, per system and per passage
| Section | Contents |
|---|---|
| `passages[]` | gold ids; every candidate with its result (`matched`, `partial`, `duplicate`, `overlap, unmatched`, `unsupported`), its matched gold id, field results, severe errors and formation status; missed gold ids; extractor outcomes; flags |
| `summary` | precision, recall (representable gold only) and F1; counts; field fidelity; severe errors per 100 candidates; grounding validity; formation counts; agreement with gold `expected_admission`. Every rate is k / n with a 95% Wilson interval |
| `severe[]` | `invented entity`, `invented assertion` / `unsupported claim`, `unsupported certainty`, `false independent corroboration` (a copy presented as first-hand), `invented time`, `pronoun admitted as a participant` |
| `adjudicate[]` | partial matches, and candidates overlapping a gold span with a different reading. **These go to a person.** Nothing is decided by an LLM, and the headline counts use exact matches only |

**Matching** (scoring-specification.md):
- **An exact match requires all of:**
  - **Source and type:** the same passage, an overlapping span and the same claim type.
  - **Participants:** every gold role has the same normalised surface (a gold pronoun's stated antecedent is
    also accepted).
  - **Statements:** the same normalised predicate.
- **A partial match:** some roles agree.
- **One-to-one:** each candidate and each gold group is used at most once. A second exact match of the same
  group is a duplicate.
- **Alternatives:** the alternative readings of an ambiguous gold assertion form one group.

**Extraction, validation and formation are kept apart:**
- **Extraction:** candidates and outcomes.
- **Validation:** `validation` outcomes and grounding validity.
- **Formation:** store statuses, and agreement with the gold `expected_admission`.

**Reproducibility:** each result records:
- the SHA-256 of `passages.csv`, the gold and `responses.json`
- the scorer, parser and response-format versions
- the sets present
- the TypeDB version (with `--formation`)

Two runs give identical results; this is covered by a test.

## Results on the developer fixtures (stage-2a/dev-harness-run.json)
**These show that the harness and interface behave as designed. They are not evidence of extraction
quality** (the passages, gold and responses are all developer-authored; development-fixtures.md).

| System | Precision | Recall | Severe errors | Formation | Agrees with expected admission |
|---|---|---|---|---|---|
| `rules:v2.1` | 14/14 | 14/24 | 0 | 12 formed, 2 review | 13/14 |
| `model:candidate-v1` (recorded, 10 of 26 deliberately faulty) | 17/17 | 17/24 | 0 | 12 formed, 4 review, 1 withheld | 16/17 |

**What the model-side run shows:**
- **Every deliberate fault was stopped or downgraded.** None formed a wrong claim:
  - 2 invalid outputs (malformed JSON, offsets supplied)
  - 2 grounding failures (an invented "Dana Okoro", a date not in the text)
  - 1 ambiguous reference ("everyone")
  - 1 cue conflict (a counterfactual called actual)
  - 1 inferred assertion refused
  - 1 organisational claimant refused
  - 1 unresolved retraction
  - 1 certainty downgraded ("I think" omitted from the evidence)
  - 1 forwarded copy forced to forwarded
- **The one disagreement with expected admission,** for both systems, is DEV-108. It is a second forwarded
  copy, and it is formed (finding F1, remaining-limitations.md).

**Tests:**
- `tests/unit/test_phase7b_harness.py`: matching tiers, duplicates, unsupported and severe errors,
  abstentions, offline operation, determinism, the corpus gate, intervals.
- `tests/integration/test_phase7b_harness_formation.py`: formation outcomes.
