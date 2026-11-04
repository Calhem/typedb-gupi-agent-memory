# Phase 7A pipeline audit

**Reproducing it:** these commands need the datasets in `.data/` and TypeDB. Their outputs, in counts, ids
and hashes only, are `audit.json`, `probe-results.json` and `counts.json`.
- `python -m gupi.benchmarks.diagnosis.audit`
- `python -m gupi.benchmarks.diagnosis.pathcompare`
- `python -m gupi.benchmarks.diagnosis.counts`

## The traced path
| Stage | Code | What it passes on |
|---|---|---|
| raw dataset | `.data/locomo/locomo10.json`, `.data/longmemeval/longmemeval_s_cleaned.json` (hashes in sample-manifest.json) | turns with speaker or role, dialogue or session ids, session dates |
| dataset adapter | `gupi.benchmarks.locomo.ingest` / `longmemeval.ingest` | one `Observation` per turn: record key, text (LoCoMo adds `[shared image: <caption>]`), observed-at (session date + position seconds), context (session), author (speaker referent / role referent) |
| TypeDB | `Memory.ingest` | `observation` with `content`, `observed-at`, authorship and containment |
| extraction input | Phase 6D `conversational._extract_and_submit` | each `Observation` in order, with earlier sets in the same conversation as `prior` |
| `rules:v2` | `RulesV2.extract` | splits sentences; tries the 14 patterns with `fullmatch` per clause; validates each candidate (`gupi.formation.validate`); invalid ones and unmatched domain-verb clauses go to `report.rejected` |
| validation and formation | `store.submit` → `formation:v1` | stores valid candidates and records a decision for each: formed (claim created atomically), withheld, review, rejected |
| TypeDB | `memory-candidate`, `formation-decision`, `formed-into`, `claim` | — |

## Checks (all turns of both splits)
| Check | Result |
|---|---|
| the extractor receives the original content | yes: adapter text equals the raw text for all 252,632 turns (LoCoMo adds the caption, as configured in Phase 5) |
| empty or truncated text | none from the pipeline. 12 LongMemEval turns are empty in the raw data; one LongMemEval sample turn ("Yes, that") is short in the raw data |
| speaker metadata | the author equals the speaker referent (LoCoMo) or role referent (LongMemEval) for every turn; TypeDB authorship is identical after a round trip |
| identifiers stable | observation ids are unique, and identical across two independent builds |
| ordering | strictly increasing within every session; LoCoMo sessions are in date order |
| timestamps | session date + position; TypeDB `observed-at` is identical after a round trip (788 LoCoMo turns; the 200 longest LongMemEval turns, up to 19,257 characters) |
| extractor invoked for every turn | yes (calls = observations) |
| input formatting | `rules:v2` expects plain sentences with capitalised names, and an author for "I"; both are present. Multi-line LongMemEval turns (47%) are split into lines, which is what the extractor's sentence rule does |
| exceptions | 0; the 6D runner does not catch them (one would stop the run), and the diagnostic code counts them |
| rejected counted as zero? | no: validation rejected 0 candidates; raw candidates = 0 |
| withheld and review separate from formed | yes (`first_decisions` counts each outcome) |
| adapter removes information | no: nothing is dropped. The only addition is the image caption |

## Path A and Path B (probe-results.json)
- **The comparison:** the ten section 6 probes ran directly (`RulesV2.extract` + `store.submit`) and
  through the adapters (wrapped as a LoCoMo conversation and as a LongMemEval session, then the 6D pathway).
- **Result:** the candidates, their content, time readings, attribution, commitment and store decisions are
  **identical on both paths for all 10 probes**.
- **Benchmark turns:** six sampled benchmark turns were run in their real conversations. Their observation
  text is identical to Path A, and so are their counts (all 0).
- **Conclusion:** any difference comes from the extractor, not the adapter.

## Independent count (counts.json)
| | LoCoMo subset | LoCoMo complete | LongMemEval subset | LongMemEval complete |
|---|---|---|---|---|
| turns examined / passed to the extractor | 289 / 289 | 5,882 / 5,882 | 12,563 / 12,563 | 246,750 / 246,750 |
| raw candidates | 0 | 0 | 0 | 0 |
| passing validation / rejected | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| withheld / review / formed | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| unparsed in-domain clauses (the extractor's own report) | 32 | 536 | 3,850 | 74,788 |
| exceptions | 0 | 0 | 0 | 0 |

**Turns with relevant or in-domain facts** come from the annotated sample, so they are estimates:
- **Relevant facts:** LoCoMo 16/30 and LongMemEval 12/30 representative turns.
- **In-domain facts:** 0/30 and 1/30.
- **Intervals:** see coverage-analysis.md.

**This reproduces Phase 6D's zero exactly,** over every turn of both datasets, including the development
splits 6D did not run.

## Confirmed defects (recorded, not fixed)
| Id | Where | Defect | Evidence | Proposed regression test |
|---|---|---|---|---|
| D1 | `rules_v2.NAME` / `WHO` | A capitalised pronoun ("She", "He", "It", "We") matches the name pattern. "She joined Halden in March 2025." becomes employment(employee "She"), is formed by formation:v1 and believed, whether or not an antecedent was given. Every "She" in one conversation then shares one referent. | probes p1-20, p1-21, p1-22, p3-07 (probes-first-run.json) | unit: no candidate, and a reported rejection, for "She works at Acme Labs.", "He joined Acme in May 2025.", "It works for Acme.", "We joined Acme in 2024."; integration: such a message forms no claim |
| D2 | `rules_v2.DOMAIN_VERB` | In-domain sentences whose verb is not in `DOMAIN_VERB` are dropped silently: "began working for", "took a job at", "quit", "resigned from", "was appointed", "is employed by", "is ... boss", "was let go". So the "unparsed in-domain" counts are a lower bound. | probes p1-02, p1-05, p1-06, p1-07, p2-02, p2-03, p2-05, p3-03, p4-04 | for each sentence: a candidate or a reported rejection, never silence |

**No input-pipeline or adapter defect was found.**
