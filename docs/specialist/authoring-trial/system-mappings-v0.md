# Mappings from each system's output to the answer contract, draft v0

Date: 2026-11-03. Status: **provisional.**
- **Review:** each mapping is reviewed by the independent reviewer.
- **Freeze:** each is frozen, with a SHA-256 in the M1 manifest, **before any held-out evaluation**. A change
  after that is a recorded amendment, made before the held-out run.
- **No code yet:** no adapter has been built. These tables are the specification the adapters must follow.

## Rules for every mapping
1. **Reformat only.**
   - A mapping turns a system's own output into the contract (scoring-protocol-v0.md §2). It may not add
     reasoning, evidence or caution that the system did not produce.
   - Where a system has no notion of something, such as uncertainty or the question's frame, the mapping
     says so and passes nothing, or a fixed value. It never supplies the missing reasoning.
2. **Deterministic.** The same system output always gives the same contract answer.
3. **Same corpus ids.** Every system ingests the same corpus, in which each segment carries its id
   (scoring-protocol §2). A mapping turns the system's own evidence pointers into those segment ids through
   a table built at ingestion. It never searches the text afterwards.
4. **Templated explanations.** Explanations are built from fixed templates that fill in the system's own
   output (claim ids, notes, retrieved passages), truncated at 80 words. Text systems that generate their
   own explanation pass it through unchanged.
5. **Losses are listed.** What a system cannot express in the contract, or what the contract cannot express
   of the system, is listed with its mapping.
6. **Tested.** Each adapter, when built, has tests on fixed example outputs, and is reviewed against this
   table before it is frozen.

## R3: GUPI (answer semantics v1, as in force)
Applies to `Memory.ask` and `Memory.query`, which return `Result` (src/gupi/query.py).

| Contract field | From GUPI |
|---|---|
| `answer.value`, yes-no | `TRUE` gives `"yes"`; `FALSE` gives `"no"`; `CONTESTED`, `UNKNOWN` and `NOT_YET_KNOWN` give `null` |
| `answer.competing` | for `CONTESTED`: `["yes", "no"]` |
| `answer.value`, entity or list questions | the label of each binding whose answer is `TRUE`: one label gives an entity answer; several give a list |
| `answer.value`, date questions | a claim boundary window that is a single day gives an ISO date; otherwise `{from, to}`, the window itself |
| `uncertainty` | `TRUE` directly supported: `stated`. `TRUE` assembled from two claims: `inferred`. `FALSE`: `inferred`, because v1 derives it from a claim's boundary, never from a direct statement about the instant. `CONTESTED`: `disputed`. `UNKNOWN`: `insufficient`. `NOT_YET_KNOWN`: `not-yet-available`. |
| `answer.frame` | `"recorded"` on questions with an `unspecified` frame. GUPI answers what is believed at a belief time, which is the recorded frame. On `actual` questions, GUPI's answer is passed unchanged. |
| `evidence` | `Result.citations`, in order: each citation's `observation_id` becomes its segment id, through the ingestion table. The first 10 distinct segments are kept. |
| `explanation` | template: "{answer} from claims {claim ids}{; notes}." |

**Losses and open points:**
- **Assembly is recorded only as a note.** v1 records an assembled TRUE only as a note on the binding. The
  adapter needs `assembled` exposed explicitly; reading the note's text is not acceptable. This is a small
  code change when adapters are built.
- **No actual frame.** GUPI cannot distinguish actual from recorded questions, so it may lose credit on
  actual-frame questions. That is a finding, not something the mapping fixes.
- **No explicit negation.** v1 cannot express an explicit negation (v2 proposal, Q4), so negation questions
  may be answered `insufficient`.

## R3 under v2 (only if ADR 0009 is accepted and implemented)
Same as v1, except:
- `PRESUMED` gives `"yes"` with `inferred`.
- `FALSE` with basis `negation` gives `stated`.
- `FALSE` with basis `termination-continuing` gives `inferred`.
- The explanation template adds the basis.

A v2 run would be reported separately from v1.

## R1 (Python objects), R2 (flat triples), R2r (reified triples), R4 (PostgreSQL)
These share GUPI's answering module (m1-protocol.md §3, §7). Their output has the same shape as R3's, so
they use **the R3 table unchanged**, with each store's own claim ids in the explanation.
- Evidence comes from each store's own record of which observation a fact came from. A store that loses
  that link, such as flat triples splitting a multi-party fact into pairs, cites what it still has. Any loss
  shows in evidence completeness.

## S-naive (latest observed wins)
| Contract field | From S-naive |
|---|---|
| `answer.value` | the value of the latest-observed claim; `null` if there is none |
| `uncertainty` | `stated` whenever there is a value, and `insufficient` when there is none. S-naive has no notion of inference, dispute or availability, and the mapping does not invent one. |
| `answer.frame` | `"recorded"` |
| `evidence` | the segment of the latest-observed claim |
| `explanation` | template: "Latest observation {segment}: {value}." |

## T-kw, T-em, T-hy (retrieval only)
| Contract field | From the retriever |
|---|---|
| `answer.value`, `uncertainty` | `null` (the system is registered as retrieval-only) |
| `evidence` | the top 10 retrieved passages, each turned into its segment id |
| `explanation` | "Retrieval only." |

These systems are scored on evidence only (scoring-protocol §2, §4.3).
- **If a rule reader is added** on top of a retriever (m1-protocol.md §3), it gets its own mapping, written
  when the reader is designed. A reader that finds no answer gives `insufficient`, never a guess.

## H-annotator: the second annotator, in the trial
In the trial, no system is run by default. The scoring pipeline is exercised on the second annotator's own
answers, mapped from their annotation by fixed rules:

| Contract field | From the annotator's `answers` sheet |
|---|---|
| `answer.value` | `value_text` (for disputed answers: `null`, with the sides' values in `competing`) |
| `uncertainty` | `status` |
| `answer.frame` | `frame` |
| `evidence` | the segments of the essential items in their first evidence set, then the other sets' |
| `explanation` | `explanation`, truncated at 80 words |

This measures the pipeline and a human reference point. It is not a system result.

**Avoiding circularity.** The adjudicated gold is partly built from the second annotator's own answers, so
scoring them against it is circular. Their frozen answers are therefore scored twice, and both scores are
reported:
- against the primary author's **frozen, pre-adjudication** gold
- against the adjudicated gold

Whether any software system is also run on the trial questions is an owner decision (README.md, Roles and
responsibilities). If one is, its result is a pipeline check, not evidence for any hypothesis.
