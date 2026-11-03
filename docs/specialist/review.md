# Specialist design review: does GUPI have a defensible advantage?

Date: 2026-11-03. Branch: `feature/specialist-evaluation`. Scope: the five documents in this folder, checked
against the code on `main` (`a6d5539`) and the Phase 2-5 results. Nothing was implemented or downloaded.

## Executive summary

- **The advantage is not demonstrated, and most of what makes GUPI's answers good is not database-specific.**
  Valid-time truth, spell assembly, the same-spell rule, conflict classification, identity grouping, time
  normalisation and proposition keys all run in Python. TypeDB holds the data, enforces typed roles and keys,
  and evaluates three status functions (believed, hypothesis, in-force supersession). PostgreSQL could do the
  same, and is *stronger* in three places that matter here: native time-range types with exclusion
  constraints, full-text indexes and vector indexes.
- **The positive evidence is weak.** Phase 4's 13/15 vs 5/15 used gold-quality claims, a world we wrote and a
  deliberately simple keyword reader. Phase 5 showed text retrieval beating structure on both public
  benchmarks once real, unstructured text was involved.
- **The specific TypeDB value is real but narrower than the hypothesis:** typed n-ary roles enforced at write
  time, a polymorphic claim hierarchy queried as one, claims about claims (evidence, reviews, supersessions)
  as first-class relations, and pattern queries over all of these without join or reification code. These are
  integrity and expressiveness properties. Whether they produce *more reliable answers* is untested.
- **The existing evaluation design cannot isolate TypeDB.** It compares text systems with GUPI-on-gold-claims,
  which mixes extraction, representation and reasoning. It needs representation ablations at equal claims: the
  same claims in plain Python objects, as flat triples, and in typed n-ary TypeDB (and optionally PostgreSQL).
- **Recommendation:** do not build the Memory Formation Engine first. Build a small, independently authored
  dataset and an evaluation that isolates the three sources of improvement, including controlled
  extraction-error injection. Make the result decide the positioning. If typed n-ary TypeDB does not beat the
  same logic over Python objects or flat triples on correctness or integrity under noise, GUPI's value lies
  in its formation and bitemporal discipline, not in TypeDB, and should be presented that way.

---

## 1. The hypothesis, and whether the architecture tests it

The hypothesis is that GUPI delivers more reliable memory for complex, evolving, contradictory knowledge
*through TypeDB's semantic modelling*. Split into parts that can be tested separately:

| Id | Sub-hypothesis | Tested by the current design? |
|---|---|---|
| H1 | Structured, bitemporal claims answer temporal, contradiction and history questions more correctly than text retrieval | Partly: only with gold claims |
| H2 | Typed n-ary roles beat flat triples or untyped records for multi-party facts | **No**: no flat-representation baseline |
| H3 | Schema-enforced typing blocks more extraction errors than application-level validation | **No**: no error-injection test |
| H4 | Doing this in TypeDB (not Python or PostgreSQL) adds correctness, integrity or productivity | **No**: no same-logic, different-store comparison |
| H5 | A formation pipeline that separates salience, support and acceptance reduces confident false answers | No: design only |

Only H1 is approached, and even then extraction quality and representation are confounded.

### 1.1 Which capabilities depend on TypeDB

| Capability | Where it runs today | TypeDB-specific? | PostgreSQL | Property graph (Neo4j etc.) |
|---|---|---|---|---|
| n-ary claims with typed roles; role-player types checked at insert | TypeDB schema | **Yes, in degree**: declared once, enforced by the database, inherited by subtypes | Join tables and check constraints or triggers; verbose but possible | Claim nodes with typed edges; weak schema enforcement |
| Polymorphic claim hierarchy (`$c isa claim` covers all subtypes) | TypeDB | **Yes** (native inheritance in queries) | Table inheritance or a generic table plus views | Labels; workable |
| Claims about claims (evidence, review, supersession link to claims) | TypeDB relations playing roles | **Yes, ergonomically** | Foreign keys to a claim table: fine | Reified nodes: fine |
| Review status at time t (believed / hypothesis / superseded) | TypeQL functions **and** a Python copy (kept in agreement by tests) | Partly: one definition inside the database | SQL function or view: equal | Cypher: equal |
| Valid-time truth, spell assembly, same-spell rule | **Python** (`temporal.py`, `answering.py`) | No | **Better**: `tstzrange`, range operators, exclusion constraints | Properties plus code |
| Conflict classification and domain constraints | **Python** over buckets that TypeDB groups | No (grouping is a `count groupby` on a Python-computed hash) | Equal, with exclusion constraints for "one value at a time" | Equal |
| Proposition grouping | Python hash stored as a string attribute | No: the n-ary structure is flattened to a string for grouping | Equal | Equal |
| Identity merging at belief time | Python union-find over accepted identity claims | No | Equal (recursive CTE) | Equal |
| Time-phrase normalisation, extraction, validation | Python | No | — | — |
| Keyword search | TypeDB `contains` scan + Python BM25 | No, and slower | **Better** (tsvector indexes) | Lucene indexes |
| Vector search | Base64 strings in TypeDB + Python cosine | No, and slower | **Better** (pgvector) | Native vector indexes |
| Schema migration with checksums | Python over TypeDB define/redefine | No | Mature tooling | Limited |

**Verdict.**
- **Genuine (but unmeasured) advantage:** declarative typed n-ary modelling with database-enforced role types,
  polymorphism over the claim hierarchy, and expressive pattern queries over claims and decisions about them.
  This shows up as less code and fewer integrity bugs, not yet as better answers.
- **Possible advantage:** status logic inside the database as one shared definition; schema-driven validation
  of extracted structures (the validator reads roles and player types from the live schema); n-ary queries
  for complex questions ("who approved what, on whose behalf, under which condition") being simpler to write
  correctly.
- **No demonstrated advantage:** temporal reasoning (Python, and PostgreSQL has better primitives),
  contradiction detection (Python), retrieval (Phase 5: text wins), vectors (absent in 3.14.1), throughput
  (about 150 claims/s ingestion; `contains` scans).

### 1.2 Database level or Python?
Mostly Python. The bitemporal *model* (attributes, events as reviews and supersessions) lives in TypeDB, but
the *reasoning* (what holds at v, believed at t; spells; contradictions) is Python over claims that TypeDB
selects. That is a defensible engineering choice, but it means "TypeDB reasons temporally" is not a claim
GUPI can currently make.

### 1.3 Could better LLM extraction explain gains on its own?
Yes, and this is the main confound. Every positive structured result so far used gold or near-gold claims.
With real extraction, answer quality will track extraction quality, and a text system with a strong LLM
reader over the same documents may match it. The evaluation must hold extraction constant across
representations, and compare against text systems with an equally strong reader.

### 1.4 What TypeDB adds in complexity
A less familiar query language with sharp edges (reserved words; `entity` as a keyword; `-> bool` rejected;
planner issues seen in other projects). No native vectors or full-text index. Slower writes for small
records. Migrations on top of define/redefine semantics. A smaller hosting and tooling ecosystem. Python
copies of database logic to keep in agreement (status rules exist in both). These are real costs, and each
needs a matching measured benefit.

---

## 2. Review of the Memory Formation Engine design

The three-decision split (salience, support, acceptance) is the strongest part of the design and
independent of the database. The weaknesses are mostly omissions.

| Area | Assessment | Recommendation |
|---|---|---|
| **Entities and identity** | Name-based suggestions only. The domain is full of role references ("the CFO", "Finance"), aliases, initials and email addresses, and of the same name used for different people. Merges are global, not time-scoped. | Add mention types (name, role reference, pronoun) and resolution *candidates with evidence*; keep merges reviewable; treat role references as claims ("the CFO" at time t), not identities. |
| **Multi-party relations** | Roles are well modelled. But role **inversion** (approver vs requester; manager vs report) passes every type check, because both players are people. | Make role inversion an explicit error class in the evaluation; schema typing cannot catch it. |
| **Time and out-of-order evidence** | `timeexpr` handles absolute and simple relative phrases. Gaps that matter in this domain: "by Friday", "end of Q2", fiscal quarters, "two weeks ago", "next month". **And a current bug:** a month without a year always resolves to the past, so "due in June" said in March becomes last June. | Make interpretation depend on tense and modality (deadlines and plans look forward); add quarter, weekday and relative-offset forms; keep the "assumption" note on every inferred year. |
| **Contradiction detection** | Pairwise rules in Python, good on states with explicit bounds. Not yet covered: events (two incompatible approvals of one item), authority (a director's correction outranks an engineer's status line), and same-source repetition. | Add an event-conflict class and a source-authority field; report contradictions separately from disagreements between sources of different authority. |
| **Reported, planned, negated, confirmed** | Proposed as "modality", not yet modelled. Without it, the commonest false-knowledge errors pass validation ("X said Y" stored as Y; "will launch in March" stored as launched; "no longer reports" lost). | Modality and attribution are **mandatory** in the first formation milestone, not optional. Negation must become an end of validity or a FALSE claim, never be dropped. |
| **Attribution and provenance** | Evidence spans and sources are solid. Missing: *who asserts* (author vs a quoted person), and source **independence**: a forwarded email is not corroboration. | Record the assertor separately from the source; give derived documents (forwards, minutes of a meeting already noted) a link to their origin, and count corroboration only across independent origins. |
| **Salience, support, acceptance** | Correct in principle. Risk: offline, "support" degenerates to exact-span checks, so every validated candidate is "explicit", and the three decisions silently collapse into one. | Gold must label all three separately, and the harness must score each decision on its own, so collapse becomes visible. |
| **Confidence** | Stored, never used, never calibrated. | Either calibrate (reliability curves against gold) or remove it from decisions. Never show an uncalibrated number to a reviewer as if it were a probability. |
| **Schema proposals** | Sound as records for humans. Risk: proposals drift into being used as data. | Keep them in a separate type that no query or answer path reads; test this. |
| **Corrections and reconstruction** | Strong already: reviews and supersessions as events, reversible, with as-of reconstruction tested. | Keep. Add tests where a correction arrives before what it corrects, from a different source. |
| **Spell assembly** | Answers TRUE when a start claim and an end claim bracket the time. With a gap (left and re-joined) this is **confident but false**, labelled only in a note. | Change the answer to a distinct "presumed" outcome (or UNKNOWN with the presumption attached) and score it separately. This would amend ADR 0007, so it needs a decision. |

### 2.1 Failure modes that create confidently structured but false knowledge
1. A false identity merge attaches one person's facts to another, everywhere, once accepted.
2. Role inversion (approver and requester swapped) passes every schema check.
3. Hearsay or a rumour stored as an assertion.
4. A plan or expectation stored as a fact ("launch in March").
5. A negation dropped, turning "no longer" into "still".
6. A wrong year from tense-blind time resolution (the June bug).
7. Spell assembly bridging an unseen gap.
8. Non-independent sources (forwards, quoted minutes) counted as corroboration and accepted by policy.
9. A structured answer displayed with citations that look authoritative even when the claim misreads the quote.

The schema stops structurally impossible facts (wrong player types, missing roles). It does not stop
*plausible* wrong facts, which are most of the list. The defence is modality, attribution, support checks,
review, and showing the quote with the answer.

### 2.2 Smallest viable implementation that tests the hypothesis
Not the full pipeline. First, the **evaluation with gold claims and injected errors** (milestone 1 below),
which needs no new extractor and decides whether representation matters at all. Then a **thin formation
slice**: source documents with offsets, modality and attribution on claims, three gold-scored decisions, and
tense-aware time. This uses a deterministic rule provider and a simulated provider, both labelled. No
plugin framework, no schema-proposal workflow beyond a record type, no acceptance policy engine beyond two
or three explicit rules.

---

## 3. Review of the projects-and-organisations benchmark design

The proposed domain is right for the hypothesis: decisions with several participants and conditions, roles
and deadlines that change, conflicting reports and corrections. It has these gaps and bias risks:

| Gap or risk | Recommendation |
|---|---|
| One programme with invented names: low diversity, and the authors know the "story" | At least 3 organisations (client, vendor, subcontractor) and 2 independent scenario threads per split; 40-60 people; documents by several fictional authors with distinct styles |
| Source authority not modelled | Give each document an author role (director, engineer, external) and include conflicts where authority decides, and some where it should not |
| Sources may already read like facts ("X is accountable for Y") | Write as real documents: minutes with tangents, email threads with quoting, status tables, chat with typos, pronouns, implicit references ("as agreed last week"). No TypeDB-shaped sentences. |
| Questions may be shaped by GUPI's features | Gold questions written by someone who has not read the code (proposed: the owner and one outside reviewer), from a fixed list of families, **before** any formation code |
| No negative controls | At least 20% of questions where text retrieval should win: verbatim wording, "which document mentioned X", fuzzy recall, long-tail details never extracted |
| Gold scoring may follow the implementation | Freeze answer keys and scoring rules (including partial credit for unknown and contested) with the dataset; record any later change as an amendment, as in Phase 5 |
| Too small to show differences | Plan for at least 150 questions per split, and report counts and confidence intervals, not just rates |
| Synthetic regularity (every fact stated once, cleanly) | Duplicate and forwarded content, partial updates, contradictory but unresolved threads, and facts never stated outright |

Neutral format: plain-text documents with metadata (author, date, kind) only; gold claims and world state in
separate files that systems never see during ingestion.

---

## 4. A fair evaluation matrix

Three possible sources of improvement are separated by varying one factor at a time.

**Extraction (what claims exist):** gold (upper-bound diagnostic) · gold with **injected errors** (role
swaps, dropped negations, hearsay as assertion, wrong years, false merges; controlled rates) · rule-based ·
simulated LLM (labelled) · real LLM (when approved).

**Representation (where claims live and how they are typed):**
R0 none (text only) · R1 Python objects in memory (same claims, same Python logic, no database) ·
R2 flat triples in TypeDB (subject, predicate, object; no typed n-ary roles) · R3 typed n-ary TypeDB (GUPI) ·
R4 PostgreSQL relational with range types (optional, needs approval).

**Reasoning and retrieval:** keyword · embedding · hybrid (text systems) · GUPI's bitemporal answering
(structured systems).

| What it isolates | Compare |
|---|---|
| Value of structure at all | R0 hybrid vs R3 with gold claims |
| Value of typed n-ary over flat (H2) | R2 vs R3, same gold claims, same answering logic |
| Value of the database vs plain code (H4) | R1 vs R3, same claims, same logic |
| Robustness and integrity (H3) | R1, R2, R3 (R4) under injected errors: false confident answers, errors rejected at write, errors flagged as conflicts |
| Value of extraction | R3 with gold vs rule vs simulated vs real LLM |
| Competitive end to end | R3 with real LLM vs hybrid text with the same LLM reader vs Graphiti with the same LLM |

**Text systems need a fair reader.** Offline, there is no strong reader, and Phase 4's rule reader is a
straw man. Report two text numbers: (a) **evidence sufficiency@k**, the share of questions whose retrieved
passages contain *all* gold evidence, including any later correction (a reader-independent upper bound);
(b) the rule reader as a lower bound. A structured system that cannot beat (a) has not shown it would beat a
good text-plus-LLM system.

**Metrics:**
- answer correctness by family
- **unsupported confident answers** (TRUE/FALSE/CONTESTED where gold is unknown)
- abstention precision and recall
- temporal accuracy, for valid time and as-of separately
- contradiction detection and classification
- citation precision and recall
- extraction precision and recall by role-filled claim, including role inversions
- salience, support and acceptance accuracy, separately
- latency, ingestion throughput and cost

The headline must be a real-extraction row, not the gold row.

**PostgreSQL** is an appropriate baseline *for representation* (R4). It answers "is TypeDB needed for this?"
directly, and it is the comparison a sceptical reviewer will ask for. It would be an evaluation-only
database, not GUPI's store, so it needs an explicit decision.

**Graphiti** is appropriate only for the end-to-end row. It needs an LLM and Neo4j or FalkorDB, and its
value is as an established temporal graph-memory system run with the same model and documents. Whether
gold facts can be loaded directly through its API should be verified before relying on that.

---

## 5. External benchmarks, reassessed

| | CronQuestions | LongMemEval (temporal-reasoning, knowledge-update, abstention) |
|---|---|---|
| Measures | Temporal QA over a given Wikidata temporal KG: time and entity lookup, before/after, first/last, time joins | Memory over long user-assistant chat: answers about changed facts, time, and unanswerable questions |
| Cannot measure | Knowledge formation from text, provenance, contradiction, review, n-ary decisions; the KG is clean and mostly binary | Organisational complexity, multi-party relations, source authority; the structured path without real extraction (Phase 5: no entity handle) |
| Adaptation | Load a documented KG subset as dated claims; route questions by their annotated type, entities and times (oracle parsing) | Already adapted for retrieval; for answers it needs LLM extraction and a reader |
| Breaks comparison with published results? | **Yes**: with oracle parsing it becomes template execution on gold structure, largely a test of the query engine, and not comparable with learned systems | Retrieval-only results are not comparable with official (LLM-judged) scores; with an LLM pipeline, comparable only if the official protocol and judge are followed |
| Licence | MIT (Wikidata CC0): commercial use fine | MIT: commercial use fine |
| Effort | Medium; ingestion of millions of facts at ~150/s is hours, so subset only | Low for retrieval (done); medium to high for answers (LLM) |
| Diagnostic value now | Low for the hypothesis; moderate as a **scale and performance test** of temporal queries | Low until LLM extraction is approved |

**Recommendation: defer the CronQuestions download.** With oracle parsing it would mostly confirm that
symbolic queries over a clean temporal KG are correct, which is not in doubt. Its useful role is a scale test
of the temporal query path, which can wait until representation ablations show that path is worth scaling.
LongMemEval's categories also wait for LLM extraction. Neither replaces the specialist dataset.

---

## 6. Consistency check of the existing documents

1. The benchmark assessment recommends LongMemEval categories, but Phase 5 showed the structured path does
   nothing there without LLM extraction. As an offline specialist benchmark it cannot test the hypothesis yet.
2. The domain design lists "one accountable party per deliverable" as a constraint. In GUPI it is post-hoc
   conflict detection, not a database constraint, so the documents should not imply enforcement.
3. The formation design's acceptance rule "corroborated by two authoritative sources" conflicts with "one
   claim per attestation" unless source independence is modelled, and it isn't.
4. The domain design compares text systems "answering from passages with a stated rule". That repeats Phase
   4's straw man, so sufficiency@k is needed.
5. The capability register lists the Claude extractor as existing. True, but it has never run live, so it
   belongs under "built, unvalidated".
6. The roadmap's Phase 6 builds baselines 1-3 plus GUPI-on-gold. That cannot isolate TypeDB: R1 and R2 are
   missing.
7. The formation design says time is "normalised deterministically". It is, but with a known wrong
   assumption (month without year resolves to the past) that the deadlines domain will hit constantly.

---

## 7. Staged implementation proposal

| # | Milestone | Scope | Tests / acceptance | Depends on | Risks | We learn | Stop or reconsider if |
|---|---|---|---|---|---|---|---|
| **M1** | **Evaluation methodology and pilot dataset** | ~40 neutral documents, 3 orgs, 2 threads; gold claims, support labels, world state; ~80 questions in fixed families incl. 20% negative controls; scoring harness with sufficiency@k; R0, R1, R2, R3 on gold claims; error injector | Gold and questions frozen before code (held-out part by the owner); harness reproducible; inter-annotator agreement measured on 20% of gold | Owner decisions D1-D3 | Gold quality; authoring time; R2/R1 implementation drifting from R3 logic | Whether representation matters at all with perfect claims, and under noise | R3 ≈ R1 on correctness **and** integrity: TypeDB's value is not correctness; reposition before going further |
| M2 | Robustness under injected errors | Error classes at 5/15/30% rates; measure unsupported confident answers, errors rejected at write, errors flagged | Per-class detection rates with intervals | M1 | Unrealistic error models | Whether schema, validation and conflict detection catch plausible errors (H3) | No representation catches role inversion, hearsay or negation errors: invest in formation checks, not schema |
| M3 | Thin formation slice | Source documents and offsets; modality and attribution on claims; tense-aware time (fix the June bug); salience, support and acceptance recorded and scored separately; rule + simulated providers | Each decision scored on its own against gold; no regression in Phases 1-5 tests | M1 | The three decisions collapse offline | How far deterministic formation gets on realistic text | Rule formation recall < 0.3 on the pilot: stop rules, wait for LLM |
| M4 | Real extraction and end-to-end comparison (needs approval) | LLM extractor and support provider through the ledger; hybrid text with the same LLM reader; Graphiti with the same model | Held-out run once; cost and latency recorded | M3, D5 | Cost; confounding by LLM quality | Whether GUPI beats text plus the same LLM end to end | No advantage over hybrid text plus reader on temporal and contradiction families: GUPI's niche is not there |
| M5 | Scale (optional) | CronQuestions subset or synthetic scale; bulk ingestion | Throughput and latency at 1M claims | M1-M2 positive | TypeDB ingestion speed | Operational viability | Ingestion makes realistic corpora impractical |
| (opt.) | PostgreSQL representation (R4) | Same claims and logic over SQL with range types | Same harness | M1, D4 | Scope creep | Whether TypeDB is needed versus a relational design | R4 ≥ R3 on every metric with less code |

---

## Conclusions

**1. Recommended architecture.** Keep GUPI's core: claims as attestations, bitemporal events, evidence,
reviews, typed n-ary claim types in TypeDB. Add only what the failure modes demand: modality and attribution
on claims, source independence, tense-aware time, and a distinct presumed outcome for spell assembly. Keep
reasoning in plain, tested Python where it is clearer, and be explicit that TypeDB's role is typed storage,
integrity and expressive queries, not temporal inference. Defer the general formation framework,
the acceptance policy engine and schema-proposal workflow until M1-M2 justify them.

**2. Recommended evaluation approach.** An independently authored, neutral-format chronological dataset with
frozen gold, scored by the matrix in section 4. Hold claims constant and vary representation (R0-R3, optional
R4); inject controlled extraction errors; give text systems a sufficiency@k upper bound; report gold rows as
upper-bound diagnostics and make the real-extraction row the headline once approved.

**3. First milestone.** M1: the pilot dataset, the harness and the R0/R1/R2/R3 comparison on gold claims and
injected errors. No formation engine.

**4. The three largest risks.**
1. **No representation effect:** the same logic over Python objects or flat triples performs as well as typed
   TypeDB. This is likely for correctness, and it would remove TypeDB as the source of advantage.
2. **Confident false structure from extraction:** role inversion, hearsay, plans and dropped negations pass
   schema checks and become authoritative-looking answers, which is worse than text retrieval's visible
   uncertainty.
3. **Self-serving evaluation:** a synthetic dataset and questions shaped by the builders, or a weak text
   reader, could manufacture an advantage. Independent authorship, negative controls and sufficiency@k are
   the safeguards.

**5. Decisions needed before development begins.**
- **D1** Accept the split hypothesis (H1-H5) and the stop criteria above.
- **D2** Who authors the held-out documents and questions (recommended: the owner plus one outside
  reviewer), and how much time is available.
- **D3** Approve M1's representation ablations (R1 in-memory, R2 flat triples), which add evaluation-only
  code but no database.
- **D4** Whether PostgreSQL may run as an evaluation-only baseline (R4).
- **D5** When and how real extraction is funded (paid budget or a local model), which M4 and Graphiti need.
- **D6** Whether to change spell assembly from TRUE to a distinct presumed outcome (amends ADR 0007).
- **D7** Confirm deferring CronQuestions, and keep LongMemEval's categories for the LLM milestone.
