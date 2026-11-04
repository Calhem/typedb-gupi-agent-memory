# Phase 7A: extraction pipeline diagnosis (sections 1–6 of the brief)

Date: 2026-11-04. Branch `feature/phase-7a-extraction-diagnosis`, from `main` at `c58d3b1`. TypeDB 3.14.1.
Diagnosis only: production extraction, formation, answering, schemas and migrations are unchanged.

**The brief arrived truncated** in section 6 ("Test expressions includin…"). Sections 1–5 and the probe
work section 6 describes are done; the rest (further probes, deliverables, completion steps) awaits the
owner.

| File | Contents |
|---|---|
| [SAMPLING.md](SAMPLING.md), [sample.json](sample.json) | The frozen sampling protocol and sample (ids and hashes only) |
| [audit.json](audit.json) | The stage-by-stage pipeline audit (`python -m gupi.benchmarks.diagnosis.audit`) |
| [annotations.json](annotations.json) | Fact-level labels, written before the extractor ran on any sampled turn |
| [classification.json](classification.json) | `rules:v2` on every sampled turn against those labels (`…diagnosis.classify`) |
| `tests/fixtures/diagnosis/probes-v1.json`, [probes-first-run.json](probes-first-run.json) | The 53 frozen probes and their first run (`…diagnosis.probes`) |

## Answer: why zero candidates
| Possible cause | Finding |
|---|---|
| 1. Input pipeline or adapter defect | **No.** Every check passes on all 225,272 held-out and 27,360 development turns (below). |
| 2. Limited domain coverage | **The main cause.** Most memorable content in both datasets is outside employment and reporting: hobbies, family, plans, purchases, places, world knowledge. |
| 3. In-domain language not recognised | **The second cause, and decisive for what is in the domain.** Every in-domain assertion in the samples (8 clear, 17 borderline) uses phrasing `rules:v2` lacks: an unnamed employer ("lost my job", "a temp job"), first-person conversational forms, tables, apposition. The probes show it recognises 4 of 39 variations on its own phrasings. |
| 4. Missing conversational context | **Present, secondary.** 24 of 85 annotated assertions need an earlier turn, mostly outside the domain anyway. |
| 5. Validation or formation | **Not a cause.** No candidate was ever produced, so neither ran. Validation rejected nothing. |
| 6. A combination | **Yes, 2 then 3,** with 4 behind them. |

So the zero is real: it is not an artefact of the pipeline. The extractor is a deliberately narrow pattern
matcher, applied to text that rarely talks about named employers or reporting lines, and that never does
so in the phrasings it knows.

## 2. Pipeline audit (audit.json)
**Path traced:** raw JSON → `gupi.benchmarks.locomo` / `longmemeval` adapter → `Observation` → TypeDB
(ingest, read back) → `RulesV2.extract` → validation (inside `extract`, and again in `store.submit`) →
`formation:v1` → TypeDB.

| Check | LoCoMo dev / held-out | LongMemEval dev / held-out |
|---|---|---|
| raw turns = observations | 788 / 5,094 | 26,572 / 220,178 (one per session version) |
| text identical to the raw turn | all (LoCoMo adds the image caption, as configured) | all |
| empty text | 0 / 0 | 0 / 12 (empty in the raw data) |
| truncated | none shorter than the raw text | none |
| ids unique; stable across two builds | yes; yes | yes |
| speaker or role preserved as author | all | all |
| order within each session increasing; sessions in date order | yes | yes |
| TypeDB round trip (content, time, author, context identical) | 788 of 788 | the 200 longest turns (up to 19,257 characters), all identical |
| extractor called once per turn; exceptions | yes; 0 | yes; 0 |
| candidates; rejected at validation | 0; 0 | 0; 0 |

**What the pipeline itself does with errors and counts:**
- **Errors:** the Phase 6D runner does not swallow exceptions; one would have stopped the run.
- **Counts:** withheld, review and formed candidates are counted separately (`first_decisions`).
- **The one counting nuance:** the 6D "in-domain sentences not parsed" figure is the extractor's own report.
  - **The report is a lower bound,** because it covers only sentences containing one of its domain verbs.
  - **Silent drops:** the probes show verbs such as "began", "took", "quit", "resigned" and "appointed" are
    dropped without a report (defect D2 below).

**Why domain-verb clauses were rejected** (a diagnostic heuristic in the audit code, not the extractor's
own reason):

| Reason | LoCoMo held-out | LongMemEval held-out |
|---|---|---|
| no capitalised name after the verb ("a hospital", "my team") | 350 | 53,836 |
| pronoun or possessive subject | 103 | 8,586 |
| other phrasing | 9 | 4,533 |
| a supported phrase inside a longer clause | 0 | 18 |

**The dominant verb** in these clauses is "work" in its everyday sense: 270 of 462 rejected clauses in
LoCoMo, and 33,662 of 66,973 in LongMemEval.

## 3–4. Domain coverage on the frozen sample
These are fact-level labels by the implementer, a single annotator, written before the extractor was run on
any sampled turn.
- **The categories:**
  - **A:** employment, reporting or appointments, and their changes
  - **A?:** borderline, mostly someone running their own business or a role at an unnamed institution
  - **B:** representable only as a provisional generic `statement` claim (subject, predicate text, object), or
    not faithfully at all
- **Which turns:** the development splits only, as in SAMPLING.md.

| | LoCoMo representative | LongMemEval representative | LoCoMo targeted | LongMemEval targeted |
|---|---|---|---|---|
| turns | 30 | 30 | 20 | 20 |
| with any potentially useful memory | 16 | 12 | 18 | 16 |
| with a supported (A) fact | **0** | **1** | 6 | 1 |
| with a borderline (A?) fact | 6 | 0 | 9 | 1 |
| with a representable but unsupported (B) fact | 11 | 11 | 11 | 15 |
| with nothing extractable (C) | 14 | 18 | 2 | 4 |
| distinct assertions (A / A? / B) | 23 (0 / 7 / 16) | 16 (1 / 0 / 15) | 28 (6 / 9 / 13) | 18 (1 / 1 / 16) |
| assertions needing an earlier turn | 8 | 4 | 6 | 6 |
| implicit (presupposed) assertions | 11 | 4 | 3 | 8 |

**Representative sample (60 turns):**
- **Assertions:** 28 turns carry 39 assertions. One is in the supported domain: a LongMemEval user stating a
  new job title at a named company.
- **Borderline:** 7 assertions, all LoCoMo "my store" or "my studio" business ownership.
- **Representable but unsupported:** 31, mostly hobbies, family, plans, purchases, residence and world
  knowledge.

**Targeted sample** (40 turns matching work vocabulary): even here, only 7 assertions are clearly in the
domain.
- **LoCoMo (6 assertions):** "lost my job" three times, "got a temp job", "accepted for an internship",
  "swamped with work".
- **In none is the employer named.**
- **LongMemEval (1 assertion):** a table of people at named companies, asserted by the assistant.

**What "representable" means here:**
- **What the schema can take:** typed `employment`, `reporting` and `identity` claims, plus the provisional
  generic `statement`.
- **Why B facts are only weakly representable:** a statement keeps free-text predicates, with no typing or
  constraints. Preferences, plans, opinions and purchases fit it badly. World knowledge fits, but it is not
  memory about the participants.
- **Unnamed employers:** A facts with an unnamed employer are representable only with a placeholder
  organisation referent. The candidate contract does not define one, and "never invent" argues against it.

## 5. Failure classification (classification.json)
**Every sampled assertion stopped before formation,** because no candidate was produced.

| Earliest stage | Representative | Targeted |
|---|---|---|
| 2 outside the implemented domain | 31 | 29 |
| 3 in-domain, unsupported vocabulary or syntax | 1 | 7 |
| 2 or 3 (borderline domain: own business, unnamed institution) | 7 | 10 |
| 4–7 (context, pronoun, temporal, attribution) as the earliest stage | 0 | 0 |
| 8 rejected by validation / 9 withheld or for review / 10 formed | 0 / 0 / 0 | 0 / 0 / 0 |

**On stages 4–7:** they occur as secondary needs, behind stage 2 or 3:
- 24 assertions need cross-turn context
- 8 need a relative date, duration or explicit date read
- 1 needs a pronoun resolved
- the assistant's table (LongMemEval) raises unverified attribution

Even with those needs met, the extractor's domain and phrasing would still stop the assertion first.

## 6. Controlled probes (probes-first-run.json, 53 frozen probes)
| Group | Should give a candidate | Did | Examples missed |
|---|---|---|---|
| the supported phrasings | 11 | **11** | — |
| synonyms and other verbs | 11 | 0 | began working for, took a job at, quit, resigned from, stopped working for, was let go, is employed by, has left, started my new job |
| sentence structure | 12 | 0 | "In March 2025, X joined", "So, X joined", a trailing clause, an embedded clause, apposition, "is the CTO at", possessives, "manages", "boss", "sorry, I meant", "I've been at X since" |
| date forms | 5 | 3 | read: "3 March", "early March", an emoji ending. Missed: "2025-03-03", "five months ago" |
| names and casing | 5 | 1 | read: first name only. Missed: lowercase organisation, a three-word name, "&", an all-lowercase sentence |
| first person | 2 | 0 | "I report to", "My manager is" |
| pronoun with an antecedent | 2 | 0 correct (2 wrong: see D1) | — |
| should give nothing | 5 | 3 correct, 2 wrong (D1) | — |

**Where the probes reached formation, it behaved as documented:**
- **Formed:** plain assertions.
- **Sent to review:** the stated correction (with its target named).
- **Formed as a negative claim:** the negation.

## Defects found (recorded, not fixed)
| Id | Defect | Evidence | Proposed regression test |
|---|---|---|---|
| **D1** | **A capitalised pronoun is taken as a person's name.** "She joined Halden in March 2025." produces employment(employee "She", employer Halden). formation:v1 forms it and it is believed. This happens with or without an antecedent, so all "She" statements in a conversation share one referent called "She". | probes p1-20, p1-21, p1-22, p3-07; `NAME` matches "She", "He", "It", "We" ("They work" escapes only because the pattern needs "works") | `tests/unit/test_formation_rules_v2.py`: for "She works at Acme Labs.", "He joined Acme in May 2025.", "It works for Acme." and "We joined Acme in 2024.", assert no candidate and a reported rejection. Integration: such a message forms no claim. |
| **D2** | **Some in-domain sentences are dropped without being reported.** The rejection report covers only `DOMAIN_VERB` (joined, left, works, reports, hired, promoted, rejoined, manages and their forms), so "began working for", "took a job at", "quit", "resigned", "was appointed", "is employed by" and "boss" vanish silently. This is the same class as the 6C "worked" fix. | probes p1-02, p1-05–p1-07, p2-02, p2-03, p2-05, p3-03, p4-04 (no report) | for each of those sentences, assert either a candidate or a reported rejection (never silence) |

**D1 is the one that matters for correctness:**
- **What goes wrong:** it creates confident false memory, a believed claim about a non-person, which then
  merges unrelated people.
- **Why the datasets did not show it:** in LoCoMo and LongMemEval, pronoun sentences also lacked a
  capitalised organisation, so it did not trigger there. It would trigger on ordinary organisational text.

## Limitations of this diagnosis
- **One annotator,** who also built the extractor, with no second opinion. The A/A?/B boundary for
  self-employment is a judgement.
- **Development splits only,** to keep the held-out data unread. The aggregate audit covers held-out too,
  and matches.
- **The rejection reasons are an evaluation heuristic,** not the extractor's own.
- **Long assistant turns** were read in full only where they had first-person content; the rest is generic
  advice.
- **Probe expectations were written by the implementer.** They test the contract's intent, not natural
  frequency.
