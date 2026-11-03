# Experimental secondary metric: scoring natural-language answers, draft v0

Date: 2026-11-03. Status: **experimental, and potentially brittle. Not the primary score. Provisional;
not frozen; no scorer has been built.**

> **Why it is experimental.** This method reads free-text answers with fixed word lists and a
> first-sentence rule. Paraphrases, unusual phrasing, and the order in which a system writes can change its
> score without changing what it means. It is therefore kept only as a secondary measure, reported
> separately and never combined with the primary score. The primary score is the structured answer
> contract in scoring-protocol-v0.md.
>
> **What it is applied to.** In the trial and M1 it scores only the optional `natural_language_answer`
> field of the contract (scoring-protocol-v0.md §8). Where this document says "the primary score" or
> "reported per system", read "this experimental metric".

**What it scores.** This rubric scores any system that answers the trial's questions in ordinary English.
It is applied against gold written to guidelines-v0.md.
- Retrieval-only systems, which return passages but no answers, are scored on evidence alone (§4), with the
  same evidence rules.
- Thresholds and any pass marks stay provisional (m1-protocol.md §2).

## 1. Principles
1. **Deterministic.** The same answer text and the same gold always give the same score.
   - The procedure uses fixed word lists, a fixed reading of the first sentence, and citations matched
     against the gold's segments.
   - **No language model judges anything.**
2. **Frozen before use.** These rules, the word lists (Appendix A) and their tie-breaks are frozen before
   any system is run on scored data. A change after that is recorded as an amendment before a held-out run,
   as in Phase 5, and never made after seeing results.
3. **Humans check the scorer; they never re-score.** Two people independently apply the rules by hand to a
   random 20% of answers (§6). Where they differ from the program, that is reported as the scorer's error
   rate. The program's score stands.
4. **Same instructions for every system** (§2). No system gets a format another cannot produce.
5. **Report the parts, not only a total.** Answer credit, evidence completeness and the flags (§5.3) are
   reported separately. The combined score is secondary.
6. **Uncertainty is rewarded when the gold is uncertain,** and penalised when the gold is definite.
   Unsupported certainty and failure to answer are counted as separate error types.

## 2. Instructions given to every system
Every system receives the same text with each question:

> Answer in plain English.
> - Your first sentence gives the answer. For a yes-or-no question, begin with "Yes", "No", or a statement
>   that it cannot be determined.
> - Cite the passages you rely on, either by their segment id in square brackets, e.g. [seg-03], or by
>   quoting at least six consecutive words exactly, in double quotes.
> - Say how certain you are, and why, if it matters.

Nothing else is required. In particular, no system is asked for a status label, a confidence number or a
structured record.

## 3. Reading an answer (deterministic feature extraction)
The steps run in this order. Each produces one feature.

**3.1 Normalise.**
- Apply Unicode NFKC, turn curly quotes straight, and collapse whitespace.
- Matching ignores case, except for the token "May" (Appendix A).
- **The first sentence** is the text up to the first ".", "?", "!" or line break that is followed by a space
  or the end, outside quotes and brackets.

**3.2 Abstention.** If the first sentence contains a phrase from **L-ABSTAIN** (Appendix A), the answer
**abstains**. Abstention takes precedence over any value in the same sentence: "No, it cannot be
determined" abstains.

**3.3 Dispute.** If the whole answer contains a phrase from **L-DISPUTE**, the answer **acknowledges a
dispute**.
- The sides it names are recorded. A side is named if any of the forms the gold gives for that side's value
  appears anywhere in the answer (guidelines §13.1). For example, "complete" for one side and "outstanding"
  for the other.

**3.4 Value.**
- **Yes-no questions:**
  - First strip one opening qualifier from **L-PREFIX** ("According to the records, ...").
  - The value is `yes` or `no` if the first remaining word is "yes" or "no".
  - Otherwise there is no value.
- **Entity, date and value questions:**
  - Each surface form in the gold is matched as a whole-word substring of the first sentence. The forms
    come from the main answer, the alternatives and the rejected candidates, through `value.forms`.
  - One gold or candidate value matched: that is the answer's value.
  - Two or more different values matched, without a dispute (§3.3): **ambiguous**.
  - None matched: no value.
- **List questions:** the set of gold items matched in the first two sentences.
- **Short-text questions:** the gold lists 2-4 key phrases, each with its accepted forms. The value counts as
  correct if at least the gold's stated minimum of them appear in the first two sentences.

**3.5 Certainty expressed,** for answers that do not abstain:
- **qualified-by-record:** the answer contains a phrase from **L-RECORD** ("the records show", "no record
  of", ...).
- **hedged:** otherwise, the first sentence contains a phrase from **L-HEDGE**.
- **certain:** neither.

**3.6 Citations.**
- A segment counts as cited if:
  - its id appears in square brackets, or
  - a quoted string of six or more words appears verbatim (after normalisation) in its text. A quote
    present in several segments, through repeats and forwards, cites each of them.
- Only the first ten distinct cited segments count. This stops a system gaining by citing everything.

**3.7 Response class.** Combining the above, each answer falls in exactly one class:

| Class | Condition |
|---|---|
| `abstains` | §3.2 |
| `dispute-both` | acknowledges a dispute and names values from both sides |
| `dispute-only` | acknowledges a dispute without naming both sides |
| `value-certain` | has a value; certain |
| `value-hedged` | has a value; hedged |
| `value-recorded` | has a value; qualified by record |
| `ambiguous` | two values without a dispute (§3.4) |
| `no-answer` | none of the above (including a yes-no answer that does not begin as instructed) |

A value is then **correct** if it matches the gold answer being compared (§5.2). Otherwise it is **wrong**;
a wrong value may match a rejected candidate.

## 4. Evidence, including answers that need several sources
**The gold's evidence sets** (guidelines §13.1):
- Each set lists only **essential** items. A set is sufficient on its own and minimal.
- Context items are never required.
- An item is covered when its segment is cited (§3.6).

**Coverage of a set** is the share of its essential items covered.

**Evidence credit e:**

| Situation | e |
|---|---|
| every essential item of at least one set is covered | **1** |
| otherwise | **0.5 × the best coverage over the sets** (always below 0.5) |
| `disputed` gold, answered `dispute-both` | 1 if, for each side, one of that side's sets is fully covered; otherwise 0.5 × the mean, over the sides, of each side's best coverage |
| gold status `insufficient` or `not-yet-available` | not applicable (the question score uses answer credit only) |

**Full credit needs all the essential evidence.**
- The question score (§5.1) reaches 1 only when e = 1.
- A correct conclusion supported by one of two required sources earns at most 0.625:
  - with one of two essential items covered, e = 0.25
  - the score is 1 × (0.5 + 0.5 × 0.25)
- A correct conclusion with no citations earns 0.5.

**Multi-source questions.**
- A question is **multi-source** if every one of its gold sets has essential items from at least two
  different documents or two different asserting sources.
- These are reported as their own subset, with the complete-evidence rate: the share of answers with
  e = 1.
- A correct conclusion with incomplete evidence is flagged **`incomplete-evidence`** (§5.3), so that a right
  answer reached without the required sources is visible, not hidden in an average.

**Evidence without an answer earns nothing.** The question score multiplies answer credit by an evidence
factor (§5.1), so citations cannot rescue a wrong or missing answer.

**Retrieval-only systems** are scored on e alone, using their top-k passages as the cited segments. This is
the existing sufficiency@k (m1-protocol.md), with these sets.

## 5. Scoring
### 5.1 Question score
For each comparison of an answer with one gold answer:
- **answer credit A**, between 0 and 1 (§5.2)
- **evidence credit e** (§4)
- **question score Q:**
  - `A × (0.5 + 0.5 × e)` when the gold answer has evidence sets
  - `A` when it has none (`insufficient`, `not-yet-available`)

The answer's score for the question is the **highest Q over all the gold answers it may be compared with**:
the main answer and any alternatives (guidelines §12.3), both frames if the question's frame is
`unspecified`, and both annotators' readings if adjudication left them `both-acceptable`. Caps apply (§5.2).

### 5.2 Answer credit A
Rows are the status of the gold answer compared with; columns are the response class (§3.7). "Correct" and
"wrong" refer to that gold answer's value.

| Gold status | value-certain | value-hedged | value-recorded | abstains | dispute-both | dispute-only | ambiguous / no-answer / wrong value |
|---|---|---|---|---|---|---|---|
| `stated` | 1 | 0.7 | 1 | 0 | 0 | 0 | 0 |
| `inferred` (not continuation) | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| `inferred`, `continuation` (recorded frame) | 1 | 1 | 1 | 0.3 | 0 | 0 | 0 |
| `disputed` (a value naming one side) | 0 | 0.3 | 0.3 | 0.4 | 1 | 0.7 | 0 |
| `insufficient` (any value) | 0 | 0.4 | 0.7 if the value matches the recorded state given in the gold's explanation, else 0.4 | 1 | 0.4 | 0.4 | 0 |
| `not-yet-available` (any value) | 0 | 0.2 | 0.2 | 1 | 0.2 | 0.2 | 0 |

For the `stated` and `inferred` rows, the value columns score a correct value. A wrong value scores 0 in
every column.

**Caps:**
- **Ambiguity calls for qualification.** When the matched gold answer is an alternative, and the main
  answer's status is `insufficient`, `disputed` or `not-yet-available`, `value-certain` is capped at 0.7.
- **Frame differences.** When the question's frame is `unspecified`, and its recorded and actual main
  answers differ, the comparison with the recorded answer is capped:
  - 1 for `value-recorded`
  - 0.7 for `value-hedged`
  - 0.4 for `value-certain`

Why these numbers:
- Hedging a plainly stated fact costs a little (0.7).
- Saying "unknown" when the records decide the recorded-frame question costs most of the credit (0.3).
- A certain answer where the gold is uncertain earns nothing.
- The numbers are provisional; the review checklist asks about them (review-checklist-v0.md, F).

### 5.3 Flags
Flags are counted and reported for each system. They are not added to Q.

| Flag | Raised when |
|---|---|
| `unsupported-certainty` | the answer is `value-certain` and its best-scoring comparison was capped, or was with a gold answer whose status is `disputed`, `insufficient` or `not-yet-available` |
| `confident-error` | `value-certain` with a wrong value, where the gold main answer is `stated` or `inferred` |
| `failure-to-answer` | `abstains` or `no-answer`, where some gold answer for the question is `stated` or `inferred` |
| `format-failure` | `no-answer` because a yes-no answer did not begin as instructed, or `ambiguous`. This is reported apart from `failure-to-answer`, so that a format problem is not mistaken for ignorance. |
| `incomplete-evidence` | A ≥ 0.7 and e < 1 |
| `rejected:<reason>` | the value matches a rejected candidate. Its reason is recorded (rumour-only, corrected, plan-only, ...). |

### 5.4 What is reported per system
Counts, with intervals and never rates alone:
- mean Q
- mean A
- the complete-evidence rate, overall and on multi-source questions
- the rate of each flag, over the questions where it can occur:
  - `unsupported-certainty` over questions whose gold is not definite
  - `failure-to-answer` over definite ones
- the histogram of rejected-candidate reasons
- results broken down by question frame (recorded, actual, unspecified) and by gold status

Questions marked `unresolvable` at adjudication are reported separately (guidelines §14.4).

## 6. The human audit of the scorer
- **Who:** two people who did not build the scorer.
- **What:** a random 20% of answers, drawn per system and fixed by a recorded seed.
- **How:** they apply §3-§5 by hand, independently, and record each feature (class, value, certainty,
  cited segments) and the score.
- **Reported:**
  - agreement between the two people
  - agreement of each with the program
  - every disagreement, with its cause, such as a phrase missing from a word list, or a citation format
- **What it changes:** the audit never changes a score. It informs the next amendment, which is made before
  the next frozen run.

## 7. Known limitations of deterministic scoring
- **Word lists miss paraphrases.** "He'd gone by then" contains no listed hedge or abstention phrase. A
  system that phrases its uncertainty unusually is scored as certain. The human audit measures how often
  this happens.
- **The first-sentence rule** penalises systems that answer late. This is mitigated by the instruction (§2),
  which every system receives.
- **Yes-no answers** must lead with "Yes" or "No" (after an optional qualifier). Non-compliance is a
  `format-failure`, reported apart, not a wrong answer.
- **Short-text answers** are scored by key phrases. This is crude, and its error rate is reported.
- **Citations are matched by segment,** not by exact span. A system citing the right email but the wrong
  sentence gets credit. Span precision is reported as a diagnostic, not scored.
- **Systems that produce templated text may match the word lists more reliably** than free-writing systems
  (bias-audit-v0.md, B14).

## 8. Worked scoring examples
These use the guidelines' examples (§16). Segment ids are illustrative.

| # | Question (gold) | System answer | Class | A | e | Q | Flags |
|---|---|---|---|---|---|---|---|
| 1 | When did Tallis start on site? (stated, 9 February 2026; set {email 12 Feb}) | "Tallis started on 9 February 2026 [seg-12feb]." | value-certain | 1 | 1 | **1** | |
| 2 | the same | "They started on 2 February 2026." | value-certain, wrong | 0 | – | **0** | confident-error, rejected:corrected |
| 3 | Was the drainage approval's condition met, and when? (inferred, combination; one set {minutes 12 May, email 20 May}; multi-source) | "Yes, on 20 May 2026, when the soil survey was completed [seg-20may]." | value-certain | 1 | 0.25 | **0.625** | incomplete-evidence |
| 4 | the same | "Yes, on 20 May 2026: the board's approval required the survey first [seg-12may], and it was completed that day [seg-20may]." | value-certain | 1 | 1 | **1** | |
| 5 | Was the soil survey complete on 30 June? (disputed; sides {table}, {chat}) | "The sources disagree: the status table says "complete", but Joaquín's chat says two boreholes were still outstanding [seg-table] [seg-chat]." | dispute-both | 1 | 1 | **1** | |
| 6 | the same | "Yes, the survey was complete [seg-table]." | value-certain, one side | 0 | – | **0** | unsupported-certainty |
| 7 | Was Ravi actually working for Tallis on 1 October 2026? (actual; insufficient; recorded state "left 30 June") | "It cannot be determined: the documents record that he left on 30 June and say nothing later [seg-1jul]." | abstains | 1 | n/a | **1** | |
| 8 | the same | "No, according to the records: he left on 30 June." | value-recorded, matches the recorded state | 0.7 | n/a | **0.7** | |
| 9 | the same | "No, he left Tallis on 30 June." | value-certain | 0 | n/a | **0** | unsupported-certainty |
| 10 | According to the documents, was Ravi working for Tallis on 1 October 2026? (recorded; inferred, continuation; set {email 1 Jul}) | "No: the documents record that he left on 30 June, with no later return [seg-1jul]." | value-recorded | 1 | 1 | **1** | |
| 11 | the same | "That cannot be determined from the documents." | abstains | 0.3 | – | **0.15** | failure-to-answer |
| 12 | Was Joaquín site lead on 1 April 2026? (unspecified; recorded: no, continuation, set {17 Mar}; actual: insufficient, with an alternative "no", combination, set {17 Mar, 20 Apr}) | "No, according to the records: he stepped down on 10 March and his return was announced for 27 April [seg-17mar] [seg-20apr]." | value-recorded | 1 (recorded answer) | 1 | **1** | |
| 13 | the same | "No." | value-certain | 0.4 (frame cap) or 0.7 (alternative cap) | 0 | **0.35** (alternative: 0.7 × 0.5) | unsupported-certainty |

In row 3, the conclusion is right but only one of the two essential sources is cited, so the score stops at
0.625. That is the rule that full credit needs all essential evidence.

In row 13, the score is the higher of the two comparisons. Both are capped because the question is
ambiguous, so the flag is raised either way.

## Appendix A: word lists (draft; frozen with the rubric)
Matched case-insensitively as whole words or phrases, except where marked.

**L-ABSTAIN:**
- cannot be determined, can't be determined, cannot determine, cannot tell, can't tell
- not possible to say, impossible to say, not known, unknown
- no information, not enough information, insufficient information
- not stated, not mentioned, the documents do not say, the documents don't say
- unclear, it is unclear, i don't know, i do not know, cannot be answered

**L-DISPUTE:**
- disagree, disagreement, conflict, conflicting, contradict, contradictory, contradiction
- inconsistent, sources differ, accounts differ, the sources disagree
- one source says, another says

**L-RECORD:**
- according to the records, according to the documents, the records show, the documents show
- as recorded, is recorded, was recorded
- no record of, not recorded, nothing records, nothing reports, no later report
- based on the documents, as far as the documents show, the documents record

**L-HEDGE:**
- might, could, possibly, probably, likely, unlikely, appears, apparently, seems
- presumably, perhaps, i think, i believe, not certain, uncertain, not sure, it is possible
- "may": **lower-case only,** so that the month "May" is not read as a hedge

**L-PREFIX** (one opening phrase removed before reading yes or no):
- according to the records, according to the documents, based on the documents
- as far as the documents show, from the documents

**Tie-breaks:** abstention, then dispute, then value. Within certainty: qualified-by-record, then hedged,
then certain.
