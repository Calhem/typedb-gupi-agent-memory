# Phase 8D.4: does structure improve answers?

**Status: protocol only. Nothing has been run.** This document was written by the builder. **Its questions must not be:** nothing developer-written is
ever called independent. The authoring brief is in [phase-8c](../phase-8c/independent-authoring-brief.md).

**The question:** does TypeDB's structured knowledge make answers more correct, even when it doesn't find more evidence? That's a different
test from recall, and the one TypeDB hasn't yet taken.

## Materials
| Item | Requirement |
|---|---|
| **Pack** | at least 60 questions, 10 per category, in invented conversations; format `gupi.phase8c-pack/1`; `check_pack` must pass |
| **Author** | someone who has not seen GUPI. Stated in the file, and the pack is hashed on receipt |
| **Gold** | the author's answers and evidence turns. Some answers are "unknown" or "disputed" |

**Categories:** relationship, temporal, conflict, historical change, provenance and uncertainty, ongoing activities.

**If no outside author is found,** a developer-written pack may be used to debug the harness only. Its results are labelled development results and
are never reported as independent.

## Three conditions
Everything is identical except the evidence block (`phase8c_answers.condition_block`).
| | Answering model sees | Tests |
|---|---|---|
| **1. Raw** | retrieved text | the baseline |
| **2. Raw + claims** | structured facts first, then text | does structure help? |
| **3. Raw + claims + qualifications** | as 2, with disputes, uncertainty, attribution and "identity not confirmed" | does GUPI's evidence model help? |

**Keeping it fair:**
- **One budget.** All three share one character limit and one ranking, and each structured line displaces raw text. Structure has to earn its space.
- **The same retrieval.** System B or C is fixed in advance, and used for all three.
- **The same prompt.** AML's instructions are used, with the caveat that its "prefer the most recent" rule may favour the raw condition on conflicts.
- **Gold evidence is reported.** A question with no gold turn in the block is a retrieval failure, not an answer failure.

## Running it without paying
**Inside the subscription only; never through a paid API.**
1. **Extraction:** a fresh session, given only the conversations.
2. **Answers:** three separate sessions, one per condition, each seeing only its own evidence blocks and the questions, with question order
   shuffled by a stated seed. **An answering session never sees another condition, the gold, or GUPI's documents.**
3. **Judging:** the AML rubric, by someone other than the answering sessions, without knowing the condition. A person is best. If a model judges,
   a sample of at least 30 goes to a person, and agreement is reported.

**Caution:** a subscription model is not `gpt-4o-mini`, so results are not AML scores.

## What is measured
| Measure | Detail |
|---|---|
| **Correctness** | per condition and category, including correctly saying "unknown" or "disputed" |
| **Harm** | answers that are confidently wrong: asserts a disputed date, treats rumour as fact, joins two people |
| **Failure cause** | `attribute` assigns each failure one first cause |
| **Fidelity** | does the answer carry the qualification when the gold requires it? |
| **Cost** | characters of raw evidence displaced by structure |

## Decision rule, fixed in advance
Paired over questions, 95% seeded bootstrap interval.
| Result | Meaning |
|---|---|
| **Condition 3 beats 1 by at least 10 points, interval above zero, and harm does not rise** | structured knowledge helps. Continue, and consider activities |
| **3 beats 2 but 2 does not beat 1** | the qualifications help and the claims alone do not. Keep the evidence layer; simplify the rest |
| **Gains only in conflict or provenance** | a real but narrow benefit. Scope GUPI around governance |
| **No gain, or more harm** | structure does not help answers. Keep raw memory and a thin evidence layer, and stop building claim structure for the AML path |

With 60 questions, a gain under roughly 10 to 15 points is unlikely to clear the interval, depending on how often the conditions disagree, so a smaller
result will read as "not shown". Each category of 10 is indicative only.
