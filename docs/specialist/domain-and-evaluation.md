# Initial specialist domain and evaluation design: project and organisational knowledge

Status: **proposal for review.** Nothing here is implemented or generated yet.

## Domain model (a new `projects` pack; TypeDB types, roles in brackets)
Entities: `person`, `organization` (existing), `team`, `project`, `deliverable`, `decision-record`,
`document` (source documents, see the formation design).

Claims (n-ary, all `sub claim`, so they inherit validity, provenance and review):
- `role-assignment` (holder, role-title value, scope: organization | team | project, appointed-by)
- `membership` (member, team)
- `reporting` (report, manager) — existing
- `responsibility` (party, deliverable, kind value: responsible | accountable | consulted | informed)
- `dependency` (dependent, prerequisite, kind value: blocks | informs) — projects or deliverables
- `deadline` (deliverable, owner, due-date value, set-by) — changes over time are new claims, not edits
- `obligation` (obligor, obligee, subject, due-date) — e.g. a contractual commitment
- `status-report` event (reporter, project, status value: on-track | at-risk | blocked | done, as-of)
- `decision` event (decider, subject, outcome value, approver, condition)
- `approval` event (approver, item, outcome: approved | rejected | conditional, on-behalf-of)
Constraints (`constraints.json`): one accountable party per deliverable at a time; one due date per
deliverable at a time; one manager per person at a time; status reports may disagree (that is data).

This exercises what the hypothesis is about: n-ary roles (an approval with approver, item, condition and
proxy), temporal validity (deadlines move; roles change), events vs states, reported vs asserted claims,
conflicts between reporters, corrections, and multi-hop dependencies.

## Dataset: a chronological stream with gold annotations
A synthetic but realistic programme ("an infrastructure migration across three teams", invented names),
about 12 months, **150-250 source documents** of mixed kinds: meeting minutes, email threads, weekly status
reports, chat messages, org announcements, a contract summary and corrections. Planted phenomena, each at
least 8 times, spread over time:
role changes and handovers; deadlines moved (some retroactively "it was always due in May"); dependencies
added and removed; decisions made, conditioned, reversed; two reporters disagreeing on status; rumours
("I heard X is leaving") that are never confirmed; planned vs actual ("we will launch in March" then it
slips); negations ("X is no longer on the project"); paraphrase and pronoun variation; information spread
across documents (start in one, end in another); irrelevant chatter (salience).

Gold, written before any extractor or query code for this domain:
- per document: the claims it supports, with roles, values, time phrases, modality and attribution;
- per (document, claim) pair: support level (explicit / paraphrased / inferred / unsupported);
- per claim: whether a careful reviewer would accept it, and when;
- the true world state over time (for validity questions).

Splits: by scenario thread (not by question), development vs held-out, fixed before work starts; at
least part of the held-out questions written by someone other than the implementer (proposed: the owner),
to avoid questions shaped by what GUPI already does.

## Questions (families, each at several belief times)
| Family | Example | Tests |
|---|---|---|
| Point-in-time state | "Who was accountable for the API cutover on 1 June?" | validity, roles |
| As known at a time | "On 15 March, what did we believe the launch date was?" | transaction time |
| History | "How has the cutover deadline changed, and who changed it?" | corrections, provenance |
| n-ary detail | "Who approved the vendor contract, on whose behalf, with what condition?" | roles |
| Multi-hop | "Which deliverables are blocked by work owned by the platform team?" | dependency chains |
| Conflict | "Do the April status reports agree about Project Atlas?" | contradiction vs differing evidence |
| Support | "Is there evidence that Dana is leaving?" (rumour only) | unsupported vs supported |
| Abstention | questions about things never stated | NOT_YET_KNOWN / UNKNOWN |
| Verbatim lookup | "What exact wording did the contract use for the penalty?" | where text retrieval should win |

Verbatim and fuzzy-recall families are included on purpose, so the evaluation can show where plain text
retrieval is better.

## Systems compared (same source material, same budget)
1. Keyword retrieval over the documents (BM25; Phase 4/5).
2. Embedding retrieval (local bge-small; Phase 5).
3. Hybrid (RRF; Phase 5), with and without structural filters.
4. GUPI structured + temporal, in three extraction settings, to separate formation from reasoning:
   (a) **oracle**: gold claims loaded directly; (b) **rules / simulated LLM**: deterministic, labelled as
   such; (c) **real LLM**: only when a budget is approved.
5. Graphiti (Apache-2.0): needs an LLM and Neo4j/FalkorDB; only with an approved LLM setting, using the
   same model as GUPI (c).
Text systems answer from passages with a stated rule offline (as Phase 4); a fair comparison of answer
quality needs the same reader model for all systems, so offline results will be reported as retrieval
plus structured-answer accuracy, with that asymmetry stated.

## Metrics
Claim extraction precision/recall (by role-filled claim); entity and relationship correctness; support-level
accuracy; acceptance agreement with gold reviewer; temporal answer accuracy (valid time and as-of);
contradiction detection precision/recall and classification (contradiction vs differing evidence);
citation precision/recall; unsupported confident answers; retrieval and answer latency; ingestion cost
and throughput (documents/s, claims/s, and tokens/$ for LLM settings).

## Risks to the evaluation
Synthetic data written by the same team that builds the system (mitigated by gold-before-code, external
held-out authorship and the external benchmarks); oracle results flattering the structured path
(reported separately and never as the headline); small size (report counts, not just rates).
