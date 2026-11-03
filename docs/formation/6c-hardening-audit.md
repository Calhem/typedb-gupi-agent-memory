# Phase 6C hardening audit: where evidence can be silently strengthened

Date: 2026-11-03.
- **Starting point:** branch `feature/phase-6-memory-formation` at `777feb1`, with a clean tree.
- **Baseline:** 310 tests passing against TypeDB 3.14.1.
- **The path audited:** source text → candidate (`rules:v2`) → validation → formation decision
  (`formation:v1`) → TypeDB claim (core/0011) → v2 answer.
- **Method:** reading the code, and probes on a disposable database, run on 2026-11-03.

**The central question:** can certainty, authority or independence grow between one stage and the next?

## Findings
| # | Finding | Severity | Components | Probe or evidence |
|---|---|---|---|---|
| H1 | **v2 answers drop the evidential qualification.** A hedged claim approved by a reviewer, or a reported or rumoured one, answers a plain TRUE or FALSE. The commitment and attribution are stored, but `AnswerResult` and `Result` say nothing about them. | **high** | `memory.ask`, `query.answer`, `answering_v2` | probe (a): "I think Alice Grey works at Acme Labs", approved, answers TRUE with no qualification |
| H2 | **Acceptance reads as authority.** A formed claim is accepted by `formation:v1` or a reviewer, then believed and answered like any other. Nothing in the answer says it was admitted into memory rather than verified. | **high** | `form`, answers | code |
| H3 | **False corroboration across documents.** A forwarded copy of an earlier statement, arriving in a *later* message, is formed as a separate claim. The `repeats` check only looks within one candidate set. | **high** | `rules_v2`, `form` | probe (b): 3 claims for one statement plus its later forward |
| H4 | **Corrections of existing claims arrive without a target.** "Correction: ..." about a claim already in memory goes to review with `suggestion = None`, so the reviewer cannot see what it would correct. Several possible targets are not flagged as ambiguous. | medium | `form` | probe (c) |
| H5 | **Reviewers can approve but not reject.** There is no way to record a reviewer's rejection of a candidate awaiting review. | medium | `form` | code |
| H6 | **A stated but unreadable date is dropped.** "joined Acme Labs in Smarch 2025" is formed as a claim with an empty valid time, with no trace that a start was stated. It looks timeless. | medium | `form`, `validate.valid_time` | probe (f) |
| H7 | **Independence cannot be judged.** Answers do not report how many independent originators support them. The same speaker repeated in two documents, a forward and an independent report would all look alike. | medium | answers | code |
| H8 | **v1 ignores the new fields.** v1 is the default and legacy semantics; it answers formed claims without qualification. | low (deferred) | `answering` | by design (do not change v1's meaning) |
| H9 | **Same name in one scope is one referent.** Two different people with the same name in one conversation are merged. This is the existing scoped-referent convention. Across sources nothing is merged. | low (deferred) | `contract.referent_id`, `form` | code; fixing it needs identity resolution, out of scope |
| H10 | **The asserter is always created as a person.** "According to Acme Labs, ..." would make a person "Acme Labs". | low | `form` | code |
| H11 | **Candidates are not stored.** Withheld and review candidates exist only in the run report; see §Persistence. | medium (decision) | `form` | candidate-persistence.md |

**Checked and found sound:**
- passages and citations are exact
- polarity is kept
- lower-bound "since" never becomes a start
- belief-time cutoff
- idempotent re-formation
- nothing merged across sources
- corrections never supersede
- old claims without the new fields are unchanged

## Outcome
| Finding | Status | Commit |
|---|---|---|
| H1, H2, H7 | **fixed:** v2 answers carry a separate qualification | `a22afa5` |
| H3, H4, H5, H6 | **fixed** within formation | `4fcbc10` |
| an unparsed domain sentence dropped silently (found by the adversarial run) | **fixed:** now reported | `0d5cc4a` |
| H8 (v1), H9 (same name in one scope), H10 (asserter kind) | **deferred,** documented | |
| H11 (candidate persistence) | **recommendation for approval** (candidate-persistence.md) | |

## What this milestone changes
- **H1, H2 and H7:** an evidential **qualification** is attached to v2 answers. It is a separate dimension;
  the temporal classifier and the status labels are unchanged.
- **H3:** a forwarded copy of a statement already in memory is withheld.
- **H4:** a correction lists the existing claims it may correct, and flags ambiguity.
- **H5:** a reviewer's rejection is recorded.
- **H6:** a stated time that could not be read sends the candidate to review, instead of forming a timeless
  claim.
- **Deferred:** H8, H9 and H10 (documented). H11 is a recommendation for approval.
