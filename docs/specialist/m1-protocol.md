# M1 evaluation-methodology pilot: protocol for approval

Date: 2026-11-03. Status: **proposal for approval. No harness, baseline or dataset has been built.**

**M1 is a pilot of the evaluation method, not a competitive benchmark. Its results must not be used for
external product claims.** It checks that the method can separate the hypotheses below, at small scale,
before the Memory Formation Engine is built.

## 1. What is being attributed to what
| Source of a difference | Measured by varying | Attributable to |
|---|---|---|
| Extraction quality | gold claims vs error-injected claims (vs real extraction, later) | the extractor, not GUPI's representation |
| Representation | Python objects vs flat triples vs typed TypeDB vs PostgreSQL, with identical claims | the modelling choice (typed n-ary or not) and the store |
| Retrieval and reasoning | text retrieval vs GUPI's bitemporal answering over the same sources | GUPI's **application logic** |

Rule: an improvement is attributed to **TypeDB** only when it appears between implementations that run the
**same application logic over the same claims** and differ only in store and representation. Equal answer
accuracy does not mean equal engineering value: integrity, query complexity, change effort and running cost
are measured separately (H2, H3, H5).

## 2. The five hypotheses
Approved in direction (2026-11-03). **All success thresholds below are provisional** until their exact values
have been reviewed; they will be fixed in the frozen guidelines before any data is written.

Each is stated as a falsifiable claim with its null in brackets. "Better" always means the 95% bootstrap
interval of the difference excludes zero; with about 48 held-out questions, small effects will be
inconclusive, and that will be reported as inconclusive.

### H1: Methodology improves answer reliability  *(application logic)*
**Claim:** over the same source documents, GUPI's method (claims as attestations, review status, explicit
unknowns, citations) gives fewer unsupported confident answers and more correct answers than text
retrieval. [no difference]
- **Baselines:** keyword, embedding, hybrid over the original documents. Each is scored two ways: (a) a
  transparent rule reader (a lower bound), and (b) **evidence sufficiency@10**: the share of questions whose
  top 10 passages contain *all* gold evidence, including later corrections (a reader-independent upper bound
  on what a good reader could do).
- **Systems:** S-gold (GUPI over gold claims; upper-bound diagnostic) and S-noisy (GUPI over error-injected
  claims).
- **Primary metric:** unsupported confident answers (TRUE, FALSE or CONTESTED where gold is UNKNOWN or
  NOT_YET_KNOWN) per 100 questions.
- **Secondary:** correctness by question family; citation precision and recall; abstention precision and
  recall.
- **Success:** S-gold beats the best text system's sufficiency@10 on correctness in the non-retrieval
  families, and S-noisy (15% errors) has at most half the unsupported confident answers of the hybrid
  rule reader.
- **Failure:** S-gold does not beat text sufficiency@10.
- **Stop / reconsider:** on failure, do not build the formation engine before revisiting the direction:
  a good text system with a strong reader would likely match GUPI.
- **Can conclude:** whether the method, given good claims, adds reliability that text retrieval cannot reach
  even with a perfect reader. **Cannot conclude:** anything about real extraction, competitors, or TypeDB.

### H2: Typed n-ary relationships improve correctness or integrity  *(modelling choice, plus TypeDB enforcement)*
**Claim:** with identical claims, typed n-ary representation answers multi-party questions more correctly and
admits fewer invalid structures than simpler representations. [no difference]
- **Baselines:**
  - R1: Python objects with the same Python validator.
  - R2: flat subject-predicate-object triples (multi-party facts split into pairs, with no claim identity).
  - R2r: reified triples (a claim node with role edges). This separates *n-ary modelling* from *any store*.
  - R4: PostgreSQL relational with constraints.
- **System:** R3 (GUPI typed TypeDB).
- **Primary metrics:** correctness on the n-ary families (decisions with approvers and conditions,
  responsibility assignments, obligations); errors stored silently under structural error injection.
- **Secondary:** errors rejected at write, by error class; errors flagged later by conflict detection.
- **Success:** R3 beats R2 on n-ary correctness, **and** R3 rejects at least 90% of structural errors
  (wrong player type, missing role) with no extra validation code, where R1 and R2 need explicit code.
- **Failure:** R3 is no better than R2r and R4 on either metric.
- **Stop / reconsider:** if R2r and R4 match R3, the benefit belongs to n-ary *modelling*, achievable in any
  store; describe TypeDB's role as convenience, not capability.
- **Can conclude:** whether typed n-ary modelling matters for these questions, and how much integrity comes
  from the database versus application code. **Cannot conclude:** that schema typing catches *plausible*
  errors (role inversion, hearsay), which it cannot by design. Those are measured, not assumed.

### H3: TypeDB improves query expressiveness and maintainability  *(TypeDB-specific)*
**Claim:** implementing the same question families and the same change requests takes less, simpler and
less error-prone code with R3 than with R1, R2r and R4. [no difference, or R3 is worse]
- **Baselines:** R1, R2r, R4.
- **Primary metric:** retrieval and query code per question family: non-blank, non-comment lines and
  tokens, plus the number of joins or traversal steps.
- **Secondary:**
  - **change effort** for two scripted change requests (add a claim type with four roles; add a question
    family needing a three-hop traversal): files and lines changed, and tests broken
  - defects found by the shared test suite during implementation
- **Success:** R3 needs at least 30% less query code across families, and no more change effort than the
  best alternative.
- **Failure:** R3 needs as much code as R4, or more.
- **Stop / reconsider:** if R4 is as concise, TypeDB's expressiveness advantage is not shown; weigh it only
  against H5's costs.
- **Can conclude:** relative implementation complexity *for this pilot, written by one implementer*.
  **Cannot conclude:** general productivity. A single implementer familiar with TypeDB biases this measure,
  so the protocol fixes the change requests in advance and reports this limitation.

### H4: GUPI handles temporal change, contradiction and correction more reliably  *(application logic)*
**Claim:** on questions about changing state, out-of-order corrections, conflicting sources and historical
reconstruction, GUPI's bitemporal logic answers more correctly, and mislabels fewer contested or unknown
cases as definite, than (a) text retrieval and (b) the same claims answered by a naive policy (latest
observed claim wins, no review status, no conflict classes). [no difference]
- **Baselines:** text systems (as in H1); S-naive, the same gold claims under a latest-wins policy.
- **Systems:** S-gold, S-noisy (GUPI, answer semantics v2 if approved, otherwise v1; reported as such).
- **Primary metrics:** correctness on the temporal families (point-in-time, as-of, history, corrections,
  conflicts); contested and unknown cases answered as definite.
- **Secondary:** valid-time and transaction-time accuracy separately; contradiction detection precision
  and recall; correct classification (contradiction vs differing evidence).
- **Success:** S-gold beats S-naive and text sufficiency@10 on the temporal families, with at most 1
  contested or unknown case per 50 answered as definite.
- **Failure:** S-naive matches S-gold.
- **Stop / reconsider:** if S-naive matches S-gold, the bitemporal machinery adds nothing on these questions;
  the dataset may lack the phenomena, or the logic may not matter. Review the dataset first, then the logic.
- **Can conclude:** whether GUPI's temporal logic matters on these phenomena. **Cannot conclude:** that it
  is implemented in TypeDB: today most of it runs in Python (see review.md). H2 and H3 cover the database.

### H5: The added complexity and cost are justified  *(TypeDB-specific, weighed against H1-H4)*
**Claim:** R3's costs over the simplest adequate alternative (R1, or R4 when persistence and concurrency are
needed) are justified by its measured benefits in H1-H4. [costs exceed benefits]
- **Costs measured:**
  - latency (p50 and p95 per question family)
  - ingestion throughput
  - peak memory
  - database size
  - new runtime dependencies
  - operational steps (services to run, migrations)
  - lines of infrastructure code
  - known TypeDB limitations hit (logged)
- **Benefits:** the measured H2-H4 differences attributable to R3.
- **Success:** R3's latency is within 2× of R4's at the pilot's scale, its ingestion is adequate for a
  10,000-document corpus in under an hour (extrapolated, stated as such), and at least one of H2 or H3
  succeeds.
- **Failure:** R3 is more than 5× slower than R4 with no H2 or H3 success.
- **Stop / reconsider:** on failure, keep the method (if H1 and H4 hold) and treat the store as replaceable.
  Plan whether to keep TypeDB on its non-performance merits, or to build on PostgreSQL.
- **Can conclude:** whether TypeDB's costs are proportionate at pilot scale. **Cannot conclude:**
  production-scale performance.

**Expected outcomes, stated before any data exists:**
- R1, R3 and R4 should give nearly identical answers on H1/H4 questions, because they run the same logic
  over the same claims.
- R2 should lose on the n-ary families; R2r should not.
- TypeDB-specific evidence can therefore only come from H2's integrity results, H3 and H5.

## 3. Systems and baselines (evaluation-only; not built until approved)
| Id | System | Input | Notes |
|---|---|---|---|
| T-kw / T-em / T-hy | keyword, embedding (local bge-small), hybrid | documents | rule reader + sufficiency@10 |
| R1 | Python objects | claims | same answering code as GUPI; same validator |
| R2 | flat SPO triples | claims (multi-party facts split into pairs) | stored in TypeDB as generic triples |
| R2r | reified triples | claims (claim node + role edges) | separates modelling from store |
| R3 | GUPI typed n-ary | claims | the system under test |
| R4 | PostgreSQL relational | claims | range types; constraints; **evaluation-only**: own container under a separate compose profile, a `psycopg` evaluation dependency group; never imported by `gupi` |
| S-naive | latest-observed-wins over claims | claims | for H4 |

All systems get the same source material, or the same claims. No paid calls. The inference budget is the
local embedding model only, timed. Gold-claim results are labelled **upper-bound diagnostic** wherever they
appear.

## 4. Controlled extraction-error injection
Applied to gold claims, one class at a time, at 5%, 15% and 30%, seeded and logged:

| Class | Example | Catchable by schema? |
|---|---|---|
| Incorrect roles: inversion | approver and requester swapped | no |
| Incorrect roles: wrong player type | an organisation as approver | yes |
| Incorrect roles: missing role | approval without approver | yes |
| Mistaken identity | two people with the same name merged; a role reference ("the CFO") linked to the wrong person | no |
| Missing negation | "no longer responsible" stored as ongoing | no |
| False temporal interpretation | wrong year; plan dated as done; end taken as start | no |
| Unsupported assertion | rumour or hearsay stored as an asserted claim; a claim with no supporting span | partly (span check) |
| Non-independent corroboration | a forwarded copy counted as a second source | no |

Metrics per class: rejected at write; flagged (conflict, review); stored silently; answers changed;
unsupported confident answers caused.

## 5. Dataset
**Size and split:** about 40 documents and 80 questions in total. The held-out authoring effort is estimated
in authoring-estimate.md; a smaller independent pilot (8 documents, 16 questions) may come first:
- *Development* (visible to the implementer): 16 documents, 32 questions.
- *Held-out* (never visible during implementation): 24 documents, 48 questions.

**Coverage required in each split:**
- three organisations (client, vendor, subcontractor), 25-40 people
- organisational relationships and responsibilities
- multi-party decisions and approvals with conditions
- project dependencies and obligations
- changing deadlines and statuses
- conflicting evidence from sources of different authority
- corrections that arrive out of chronological order
- historical reconstruction
- unknown and contested answers
- negative controls

**Question families and quotas (per split, as a share of questions):**

| Family | Share |
|---|---|
| Straightforward retrieval (negative controls: verbatim wording, which document said X, details never structured) | **at least 20%** |
| Point-in-time state | 10-15% |
| As known at a time (transaction time) | 10-15% |
| History and corrections | 10-15% |
| n-ary detail (who approved, on whose behalf, under what condition) | 10-15% |
| Multi-hop (dependencies, reporting chains) | 5-10% |
| Conflicting reports | 5-10% |
| Unknown or contested (gold UNKNOWN, NOT_YET_KNOWN or CONTESTED) | at least 10% |

**Neutral format:** plain-text documents with metadata only (id, date, author, author role, kind,
reply-to/forward-of). Kinds: meeting minutes, email threads with quoting and forwards, status tables, chat
with typos and pronouns, an announcement, a contract summary. No document contains structured or
TypeDB-shaped facts. Gold claims, world state and answers live in separate files that no system reads
during ingestion.

## 6. Authoring protocol and independence
1. **Guidelines first.** One document fixes:
   - domain scope and document kinds
   - question families and quotas
   - gold formats
   - answer statuses and evidence sets defined independently of any system (draft:
     authoring-trial/guidelines-v0.md, which is not derived from GUPI's schema or ADR 0009)
   - scoring, including partial credit, through a fixed mapping from each system's output onto the
     guidelines' statuses. For example, a system's PRESUMED against an `inferred` gold, or FALSE by explicit
     negation against FALSE by continuation, are scored apart. The mapping is written before any held-out
     run and applied to all systems alike.
     The draft is authoring-trial/scoring-protocol-v0.md (a common structured answer contract). It is deterministic, uses no LLM judge, and gives full
     credit only with all essential evidence.
   - error classes

   It is written **without reference to GUPI's schema** and reviewed by the owner. A draft (v0) is tried in
   a **two-document authoring trial** (authoring-trial/README.md), which records authoring time, annotation
   disagreements and representational limitations. The guidelines are revised from it, then frozen before
   the eight-document mini-pilot. No data for the mini-pilot or either split is written before that freeze.
2. **Roles.**
   - The **implementer** writes only the development split and the code.
   - **Held-out authors** (proposed: the owner, and ideally one outside reviewer) write the held-out world,
     documents, gold and questions from the guidelines alone, without reading GUPI's code or schema.
   - A **second annotator** independently annotates 20% of each split's gold.
3. **World script.** Each split starts from a dated timeline of organisations, people, roles, decisions,
   deadlines, dependencies and reports, written in a neutral spreadsheet. It is the source of truth for
   world-state gold and is never ingested.
4. **Documents.** Written from the world script in natural prose, by the split's author. They include:
   - irrelevant chatter
   - facts implied but never stated
   - pronouns and role references
   - duplicates and forwards
   - unconfirmed rumours
   - late corrections
5. **Gold, per document:**
   - claims with roles, values, modality (asserted, reported, planned, negated) and assertor
   - quoted time phrases, with explicit vs inferred dates
   - support level per (document, claim)
   - salience
   - reviewer acceptance and its time

   Agreement on the double-annotated 20% is reported (role-filled-claim F1; Cohen's kappa for support and
   acceptance). Disagreements are adjudicated and logged.
6. **Questions and answers.** Written by the split's author from the world script and documents, each with
   a gold answer kind, binding, evidence documents and the rule used. Answers are fixed **before** any system
   is run on that split.
7. **Freezing and access.**
   - The development split is committed when complete.
   - The held-out split stays **outside the repository and outside the implementer's access** (owner's
     storage); only a SHA-256 manifest of its files is committed, before implementation starts.
   - After the harness and all systems are frozen at a tagged commit, the owner runs or releases the held-out
     split once.
   - Results and the split are then committed. Any amendment must be recorded before the held-out run, as in
     Phase 5.

## 7. Preventing tailoring to TypeDB (bias controls)
- Held-out authors work from domain guidelines, not GUPI's schema. The guidelines are reviewed for
  TypeDB-shaped wording before freezing.
- At least 20% of questions are straightforward retrieval, where text should win, and are scored as such.
- Some phenomena are deliberately awkward for GUPI's model:
  - free-text detail
  - numbers in tables
  - facts never stated outright
  - long verbatim clauses
  - role references
- **Schema coverage** is reported: the share of gold facts that GUPI's existing claim types can express.
  Uncovered facts count against structured systems; they are never dropped.
- Text systems are scored with sufficiency@10, so a weak rule reader cannot manufacture a structured
  advantage.
- Gold-claim rows are labelled upper-bound diagnostics; error-injected rows are reported beside them.
- One implementer writing R1, R2r, R3 and R4 is a bias (familiarity with TypeDB). It is mitigated by:
  - one shared answering module for all
  - a shared test suite
  - change requests fixed in advance
  - an outside review of the R4 schema before the run, if a reviewer is available
- Counts and intervals are reported, not just rates; inconclusive results are reported as inconclusive.

## 8. Overall stop conditions
- H1 or H4 fails: revisit the specialist direction before building the formation engine.
- H1 and H4 hold, but H2, H3 and H5 fail: continue the method, and describe TypeDB as an implementation
  choice, not the source of advantage.
- Gold agreement below F1 0.8 or kappa 0.6: fix the guidelines and re-annotate before trusting any result.

## 9. Decisions needed to start M1
1. Approve the five hypotheses, metrics, thresholds and stop conditions (or amend them).
2. Confirm the held-out authors and second annotator, and the time available.
3. Confirm PostgreSQL as an evaluation-only container (separate compose profile; `psycopg` in an evaluation
   dependency group; never imported by `gupi`).
4. Decide whether GUPI runs in M1 with answer semantics v2 (v2-truth-semantics.md, ADR 0009) or v1. The
   Q1-Q8 directions were approved on 2026-11-03. This no longer blocks the guidelines, which are neutral
   (authoring-trial/guidelines-v0.md); it decides only how GUPI's outputs are mapped onto the gold statuses.
5. Review the two-document trial's report before the mini-pilot starts. The success thresholds stay
   provisional until reviewed; the trial does not set them.
