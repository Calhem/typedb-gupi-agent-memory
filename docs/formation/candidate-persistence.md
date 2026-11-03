# Candidate persistence: assessment and recommendation (for approval)

Date: 2026-11-03. Status: **option C approved and implemented.** See candidate-store.md.

## What exists today
Each formation run is stored as an `extraction-run` (method `formation:v1`) whose `run-report` is a JSON
string. It lists every decision: candidate id, outcome, reason, decider, claim id, and any correction
suggestion. Formed claims are linked to the run by `extraction-output`, and carry `candidate-id`
(core/0011). **Candidates themselves are not stored.**

## The questions
| Question | Answer |
|---|---|
| **What is lost when candidates stay only in run reports?** | The candidate's content. For withheld candidates (plans, hypotheticals, copies, inexpressible times) and those awaiting review, only an id and a reason survive. Lost entirely: the passage and offsets, participants, every time reading (phrase, window, precision, assumption, unread phrases), modality, commitment, attribution and relations. For formed claims, the bounds and attributes survive, but the time readings do not (audit A7). |
| **Can extraction be reproduced deterministically?** | **For `rules:v2`, yes, given the same observation text and the same earlier candidate sets of its thread, in the same order.** Prior sets are needed to name correction targets, and they too are not stored. **For an LLM extractor (6D), no.** Re-extraction can give different candidates and different ids, so an approval given for one id may match nothing later. |
| **Can a reviewer approve or reject a specific candidate later?** | **Only by re-running its extraction and passing `approvals` or `rejections` by id.** There is no queue of pending candidates. `Memory.review_queue` lists claims, not candidates. A reviewer would have to read run-report JSON to find what awaits review, and its content is not there. |
| **Do correction suggestions survive process restarts?** | **They are durable,** inside the run-report string in TypeDB. **But they are not queryable or linked** to the claims they name, so nothing can list "corrections awaiting a decision about claim X". Re-forming recomputes them. |
| **What is the minimum for a usable review workflow?** | 1. a durable record of each candidate's exact content (payload) and version; 2. a queryable list of what awaits review; 3. reviewer decisions (approve or reject, by whom, when) as historical events, like claim reviews; 4. a link from a candidate to its observation, and to the claim it became; 5. correction suggestions linked to their target claims. |

## Options
| Option | What it means | Assessment |
|---|---|---|
| **A. Continue without candidate persistence** | Keep the run reports only. | **Adequate only for deterministic, rule-based demonstrations.** It meets none of the minimum requirements 1-5, and it breaks once a non-deterministic extractor is used (6D). |
| **B. A minimal durable queue using existing structures** | For example: store review candidates as unreviewed claims (hypotheses), or parse run-report JSON into a queue. | **Not recommended.** Claims that are plans or hypotheticals would enter memory as claims (forbidden by the 6C rules). JSON queues are not queryable, and cannot carry history. Either way it adds structure that a proper store would replace. |
| **C. core/0012 (minimal)** | An additive store, apart from claims, for the candidate payload and links. Reviewer decisions reuse the existing `review` relation, so approval and rejection are historical events with the same machinery as claim reviews. | **Recommended.** It meets 1-5 with one additive migration, and it is required before 6D. |

## Recommendation: C, a minimal core/0012
This is a narrower version of 6c-design-checkpoint.md §3:

```text
entity memory-candidate, owns gupi-id @key, owns ir-version, owns candidate-payload, owns method,
  owns recorded-at, owns proposition-key, owns candidate-outcome;   # formed | withheld | review | rejected
relation candidate-of, relates candidate, relates observation;
relation formed-into, relates candidate, relates claim;
relation correction-suggestion, relates suggested-by, relates target @card(0..);  # candidate -> claims; never applied
memory-candidate plays review:reviewed;            # approve / reject as reviews, with their history
memory-candidate plays extraction-output:output;   # linked to its formation run
```

**Rules for it:**
- **A candidate is never believed, never answered from, and never a claim.**
- **Rejected candidates stay stored,** distinguishable by their outcome and reviews.
- **The existing claim review queue is unchanged.** A separate candidate queue lists `review` outcomes.
- **Additive only.** Rollback means restoring the pre-migration export.

**Not in it:** decomposing the payload into separate TypeDB types, a general `candidate-relation`, and any
change to answering.

Implementation would wait for approval, and would be the first step of the next milestone.
