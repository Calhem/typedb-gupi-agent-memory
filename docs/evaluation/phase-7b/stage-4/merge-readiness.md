# Merge readiness: `feature/phase-7b-stage-4-evidence-integrity` into `main`

**Date:** 2026-11-05. **Scope:** everything since `main` (`6a71fcb`): Stages 3A, 3B, 3C and 4. **Status: ready for
the owner's decision. Not merged.**

## Results
| Check | Result |
|---|---|
| Target branch | `main` equals `origin/main` and is an ancestor of this branch: a fast-forward, no conflicts possible |
| Full suite with TypeDB 3.14.1 | **579 passed, 19 expected failures, 0 skipped** (main's known limitations; the count of expected failures is unchanged) |
| Production code changed since `main` | `formation/form.py`, `formation/model_candidate.py`, new `formation/fidelity.py`; `benchmarks/phase7b/stage3.py` (evaluation tooling). Schema: none. Migrations: none |
| Compatibility | no candidate-format or response-format change; recorded responses still parse; 1.0 candidate ids unchanged |
| Privacy | no gold values, raw responses, individual decisions, local paths or secrets in the added lines. The public passages and field names are public by design (Stage 3A) |
| Frozen evaluation | gold v1 hash matches the manifest; 32 response hashes verify; `public/`, `manifests/` and `results/` unchanged; private repository clean |
| Replay of Stage 3B responses | run twice from clean databases: byte-identical to each other and to the committed record. 31 candidates; 14 formed, 8 review, 9 withheld; formed severe errors 3 → 0 |
| Spending and model calls | none |

## What the review found and fixed
| Commit | Problem | Fix |
|---|---|---|
| `e2b251e` | R1 matched predicates as substrings: "owns" verified inside "Halden disowns Pellwick", which would have formed | whole-word matching; test fails without the fix |
| `34e5243` | R2 was skipped when a model response failed to parse, so a broken response could hide a retraction | retractions are read on that path too; test fails without the fix |
| `477cef8` | a future manifest would not hash the new `fidelity.py` | added to the code-hash list; the frozen Stage 3A manifest is unchanged |

## The specific confirmations
- **R1 false positives:** 19 constructions were probed: 16 formed and 3 went to review. Complete predicates form ("acquired", "met with",
  "is a subsidiary of", "invested in", "acquired an 80% stake in"), including mixed case, line breaks and later
  adverbials. The three sent to review are deliberate: a preposition left out of the predicate, a stake
  overstated as the whole object, and a possessor. These are pinned by tests.
- **R2:** a pending retraction survives a new connection with its null target, suggestion and history. Submitting,
  approving or rejecting it leaves decided answers and the believed set exactly as they were (test with a TRUE
  answer, both verdicts).
- **R3:** an approved fact from an allegation comes back through retrieval as `reported`, commitment `unknown`,
  standing `qualified`, `definitive: false`, with the alleger as originator and the reviewer as acceptor. The
  temporal answer stays a separate dimension.

## Remaining risks
**To decide before automated model integration:**
1. **R2 and R3 cover the model interface only.** The older `gupi.extraction` pipeline (`ClaudeExtractor`) writes
   claims as unreviewed hypotheses without passing through `form.decide`, so none of R1–R3 applies to it. Any
   future model integration should use `model:candidate-v1.1` and the candidate store.
2. **An unrecorded retraction is not durable.** "Scratch that." (no "I") or a message with no author gives
   `bare-retraction-unrecorded` in the extraction report only; nothing is stored.
3. **Pending retractions do not appear in answers.** They are in the review queue, not flagged on the claims they
   may affect, so an answer can still rest on a claim someone has asked to retract.

**Accepted limits:**
4. **R1 is structural and R2/R3 are lexical.** A misleading predicate with an adjacent object, or a retraction or
   allegation in unlisted wording that the model does not mark, is still missed.
5. **Review volume rises.** Nothing measures reviewer capacity yet. In the replay, review doubled from 4 to 8.
6. **The replay is a check on the same corpus the failures came from.** It shows the observed cases are closed,
   not that the failure classes are gone. Stage 3C's model-assisted figures are not re-scored here.

**Carried over:** no independent human adjudication; item 9's gold question; "former" (R4), surname coreference (R5),
same-named people (S8), paraphrased copies (L4); no externally written corpus (R10). One passage line quoted in the
Stage 3C README since `713bc80` remains public (invented text, not gold).

**After a fast-forward,** `main` carries Stages 3A–3C and 4 together; the Stage 3C feature branch can then be retired.
