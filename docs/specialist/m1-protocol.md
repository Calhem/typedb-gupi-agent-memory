# M1 evaluation-methodology pilot: protocol for approval

Date: 2026-11-03. Status: **proposal for final approval; nothing built.**

**M1 is a pilot of the evaluation method, not evidence of competitive differentiation. Its results must not
be used for external product claims.** It tests whether the method can tell the hypotheses apart, at small
scale, before any formation engine is built.

## Two questions, kept apart
- **Methodology (M):** does GUPI's knowledge-management method (claims as attestations, review status,
  bitemporal answers, conflict classes, explicit unknowns) make answers more reliable than text retrieval
  over the same material?
- **TypeDB (T):** does implementing that method in TypeDB improve correctness, integrity, query
  expressiveness, maintainability or performance compared with other implementations of *the same method*?

A positive M result says nothing about T, and vice versa.

## The five hypotheses
| Id | Hypothesis (null in brackets) | Compares | Primary metric |
|---|---|---|---|
| **M-H1** | With identical gold claims, GUPI's method gives more correct answers and fewer unsupported confident answers than text retrieval on temporal, as-of, conflict and abstention questions [no difference] | S-gold (method over gold claims) vs best text system's **evidence sufficiency@10** and its rule-reader score | Correct answers per family; unsupported confident answers |
| **M-H2** | Under injected extraction errors, the method's safeguards (review status, conflict classes, explicit unknowns) reduce unsupported confident answers compared with the same claims answered without them [no difference] | S-noisy with safeguards vs S-noisy with safeguards disabled (every claim treated as accepted, no conflict check) | Unsupported confident answers per error class |
| **T-H1** | Correctness: typed n-ary TypeDB (R3) answers more questions correctly than the same method over Python objects (R1), naive binary triples (R2) and PostgreSQL (R4), with the same claims [no difference] | R1, R2, R3, R4 | Correct answers, by family (n-ary families separately) |
| **T-H2** | Integrity: R3 rejects or flags more injected structural errors at write time than R1, R2 and R4 given equal validation effort [no difference] | R1-R4 under error injection; R1 and R4 get the same Python validator; R4 also gets SQL constraints | Errors rejected at write; errors flagged later; errors silently stored |
| **T-H3** | Expressiveness, maintainability, performance: R3 needs less query code and less change effort per question family, at acceptable latency [R3 is not simpler, or is too slow] | R1-R4 | Lines and tokens of retrieval/query code per family; files changed to add one new claim type and one new question family; latency p50/p95; ingestion throughput |

Expected outcomes, stated in advance: **T-H1 is likely null.** R1, R3 and R4 run the same Python answering
logic over the same claims, so differences can only come from candidate selection bugs. R2 (naive binary
triples) should lose on n-ary questions. That loss is a property of the *modelling choice*, achievable in
any store with reification, not of TypeDB. The TypeDB-specific evidence will come from T-H2 and T-H3.

## Systems
- **Text (R0):** keyword, embedding (local bge-small), hybrid; each reports evidence sufficiency@k (all gold
  evidence, including corrections, in the top k), plus a rule reader as a lower bound.
- **S-gold / S-noisy:** GUPI's method over gold claims, and over gold claims with injected errors.
- **R1** Python objects in memory · **R2** naive binary triples (subject, predicate, object; n-ary facts split
  into pairs) stored in TypeDB · **R3** GUPI typed n-ary TypeDB · **R4** PostgreSQL relational, evaluation-only
  (range types; run by the harness in its own container; never a GUPI dependency).
- All systems ingest the same documents (text systems) or the same claims (structured systems); all are
  offline and use no paid calls; inference budget: none beyond the local embedding model.

## Error injection (for M-H2 and T-H2)
Applied to gold claims at fixed rates (5%, 15%, 30%), each class separately, seeded and recorded:
1. role inversion (approver and requester swapped)
2. wrong player type (an organisation in a person role)
3. missing required role
4. dropped negation ("no longer" becomes ongoing)
5. hearsay stored as an assertion
6. plan stored as a fact
7. wrong year
8. false identity merge
9. duplicate from a non-independent source

Classes 2-3 are structural, which a schema can catch; the others are plausible, which no schema can catch.

## Success criteria and stop conditions
Small pilot, so every rate gets a 95% bootstrap interval; "better" means the interval of the difference
excludes zero.

| Hypothesis | Counts as support | Stop or reconsider if |
|---|---|---|
| M-H1 | S-gold beats text sufficiency@10 on temporal, as-of, conflict and abstention families; at most 1 unsupported confident answer per 50 questions | S-gold does not beat text **sufficiency@10**: a good text system plus a strong reader would likely match GUPI; reconsider the specialist claim |
| M-H2 | Safeguards cut unsupported confident answers by at least half for at least 4 of the 7 plausible error classes | Safeguards help on fewer than 2 classes: the method's reliability claim rests on extraction quality alone |
| T-H1 | R3 > R1/R4 (unlikely) | R1 ≈ R3 ≈ R4 (expected): TypeDB adds no correctness; positioning must rest on T-H2/T-H3 or on the method |
| T-H2 | R3 rejects or flags at least 90% of structural errors (classes 2-3) with no extra validation code, where R1 needs explicit code for the same | R4 with constraints matches R3: no integrity advantage over PostgreSQL |
| T-H3 | R3 needs at least 30% less query code across families, with no worse change effort, and latency within 2× of R4 | R3 is not simpler than R4, or is more than 5× slower: TypeDB's practical advantage is not shown |

Overall stop rule: if M-H1 fails, do not build the formation engine before revisiting the direction. If M-H1
holds but T-H1 to T-H3 all fail, continue the method but describe TypeDB as an implementation choice, not
the source of advantage.

## Dataset-generation protocol
**Roles.**
- *Implementer:* writes code and the development split only.
- *Held-out author(s):* proposed: the owner, and ideally one outside reviewer. They write the held-out
  documents, gold and questions, which the implementer never sees before the frozen run.
- *Second annotator:* double-annotates 20% of gold.

**Steps.**
1. **Guidelines first.** One committed document fixes the domain scope, document kinds, question families
   and quotas, gold formats, answer-kind definitions (including PRESUMED under answer semantics v2), the
   scoring and partial-credit table, and the error-injection classes. It is frozen before any data is
   written.
2. **World script, per split.** The author writes a dated timeline in a neutral spreadsheet or YAML:
   - 3 organisations (client, vendor, subcontractor), 40-60 people
   - roles and responsibilities
   - decisions with participants and conditions
   - deadlines and their changes
   - dependencies
   - status reports by authors of differing authority
   - corrections that arrive late
   - rumours that are never confirmed
   - facts never stated outright
   - irrelevant chatter

   The world script is the source of truth for world-state gold and is never ingested.
3. **Documents.** Plain text with metadata only (id, date, author, author role, kind, reply-to/forward-of):
   minutes, email threads with quoting and forwards, status tables, chat with typos and pronouns, an
   announcement, a contract summary. No sentence is written to fit GUPI's schema or rule patterns.
   Development: about 25 documents; held-out: about 25, from different scenario threads.
4. **Gold, per document:**
   - claims with roles, values, modality, assertor and quoted time phrases
   - support level for each (document, claim) pair
   - salience
   - a reviewer's acceptance and its timing

   Written by the document's author, double-annotated on 20%, with agreement reported (role-filled-claim F1;
   Cohen's kappa for support and acceptance). Disagreements are adjudicated and logged.
5. **Questions:** about 50 per split, from fixed families with quotas, at several belief times:
   - point-in-time state
   - as known at a time
   - history and corrections
   - n-ary detail
   - multi-hop dependencies
   - conflicting reports
   - support versus rumour
   - abstention
   - **at least 20% negative controls** where text retrieval should win (verbatim wording, which document
     said something, details never extracted)

   Each has a gold answer kind, binding, evidence documents and the rule it was judged by.
6. **Freezing.** The development split is committed when written. The held-out split stays **outside the
   repository** (owner's storage); only its SHA-256 manifest is committed, before implementation starts. It
   is delivered once, after the harness and all systems are frozen at a tagged commit, and is committed after
   the run with the results.
7. **Bias safeguards:**
   - different authors for development and held-out
   - questions written without reading the code
   - negative-control quota
   - text systems scored with sufficiency@k, not only a weak reader
   - gold-claim rows labelled "upper-bound diagnostic"
   - counts reported with intervals
   - any amendment recorded before the held-out run, as in Phase 5
8. **Licence:** synthetic content written for GUPI, released with the repository (Apache-2.0) after the run;
   no real organisations or people.

## Deliverables of M1
Frozen guidelines; development split; held-out manifest; harness; R0-R4 and S-gold/S-noisy systems; one
held-out run; a report that answers each hypothesis as supported, not supported, or inconclusive, labelled
as a methodology pilot.

## Decisions needed to start M1
1. Approve the five hypotheses, metrics and stop conditions above (or amend the thresholds).
2. Confirm who authors the held-out split and second annotations, and the time available.
3. Approve PostgreSQL as an evaluation-only container for R4 (a separate compose profile; a `psycopg`
   evaluation-only dependency group).
4. Approve answer-semantics v2 for M1 (see joined-spell-analysis.md), with v1 preserved for past results.
