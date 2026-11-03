# Scoring protocol: common answer contract, draft v0

Date: 2026-11-03. Status: **provisional draft for independent review. Not frozen; no scorer has been
built.**

**Scope.** This is the **primary** scoring method for the trial, and later for M1. It replaces
first-sentence parsing and fixed word lists for the primary score. The earlier natural-language rubric is
kept only as an experimental secondary metric (scoring-nl-experimental-v0.md, §8). Gold is written to
guidelines-v0.md (revision 2). Thresholds and pass marks stay provisional (m1-protocol.md §2).

## 1. Principles
1. **One contract for every system.**
   - Every evaluated system returns the same structured answer (§2), whatever it is built on: a
     database-backed memory, a relational baseline, a text reader, or a person.
   - The instructions and label definitions (Appendix A) are identical for all.
2. **The structured fields are scored deterministically.** The same answer file and the same gold always
   give the same score. No language model is used anywhere in scoring.
3. **Explanations are audited, not scored.**
   - People check the free-text explanation, and whether the cited evidence actually supports the answer
     (§6).
   - The audit's results are reported as separate measures. They never change the primary score.
4. **The parts are reported, not only a total.** Answer credit, evidence completeness and the flags are
   reported separately. The combined score is secondary.
5. **Frozen before use.** The contract, the matching rules and the credit table are frozen before any system
   is run on scored data. Changes are recorded amendments made before a held-out run, never after seeing
   results.

## 2. The answer contract
Each system writes one JSON object per question, in a JSON Lines file per run:

```json
{"question": "q-07",
 "answer": {"value": "no", "frame": "actual"},
 "uncertainty": "inferred",
 "evidence": [{"segment": "seg-17mar"}, {"segment": "seg-20apr", "quote": "back as site lead from next Monday"}],
 "explanation": "The minutes report that he stepped down on 10 March; on 20 April the contractor says he returns the following Monday, so he was not site lead on 1 April."}
```

| Field | Required | Content |
|---|---|---|
| `question` | yes | the question id |
| `answer.value` | yes (may be `null`) | **yes-no:** `"yes"` or `"no"`. **entity:** a name, as a string. **date:** an ISO date (`"2026-02-09"`), or a range `{"from": ..., "to": ...}`, with `to` exclusive. **value:** a string such as `"12 boreholes"` or `"£4,500"`. **list:** an array of strings. **short-text:** a string of at most 30 words. `null` when the system gives no value. |
| `answer.competing` | only with `disputed` | an array of the competing values, each in the form above |
| `answer.frame` | when the question's frame is `unspecified` | `"recorded"` or `"actual"`: the reading the system answers |
| `uncertainty` | yes | exactly one of `stated`, `inferred`, `disputed`, `insufficient`, `not-yet-available` (definitions in Appendix A) |
| `evidence` | yes (may be empty) | up to 10 items `{"segment": id, "quote": optional}`. Each `segment` is an id from the supplied corpus. `quote` is an optional verbatim excerpt of at most 50 words, used only by the audit. |
| `explanation` | yes | at most 80 words, in plain English |
| `natural_language_answer` | no | free text, used only by the experimental metric (§8) |

**The corpus every system receives** marks each segment with its id in the text itself (for example a line
`[seg-03]` before each message). Any system, including one that only reads text, can therefore cite
segments.

**Retrieval-only systems** are registered as such. They return `answer: null` and `uncertainty: null`, with
their top passages in `evidence`, and are scored on evidence only (§4).

## 3. Validating the contract
Validation is deterministic. The only normalisation is: trim whitespace, apply Unicode NFKC, and lower-case
the enumerated fields (`uncertainty`, `frame`, yes-no values). Nothing else is repaired.

An answer fails validation if it:
- is not valid JSON, or is missing a required field
- has an unknown enumerated value
- has a value of the wrong type for the question's answer type
- cites a segment id not in the corpus
- exceeds the stated limits

A failing answer is scored as giving no value (A = 0) and flagged `contract-failure`. Contract failures are
reported separately for each system, so that a formatting problem is not mistaken for a wrong answer.

## 4. Deterministic scoring
### 4.1 Value correctness c (0 to 1)
Comparison is with a gold answer's value and its `forms`. Normalisation:
- NFKC
- case-folding
- collapsing whitespace
- trimming punctuation at the ends

| Answer type | Rule |
|---|---|
| yes-no | c = 1 if equal, otherwise 0 |
| entity | c = 1 if the normalised value **equals** one of the gold forms. Substrings do not count. Otherwise 0. |
| date | **Inside** the gold range (a date, or a range contained in it): c = 1. **Containing** the gold range but wider (a coarser answer, e.g. "February" for 9 February): c = 0.5, "imprecise". **Otherwise:** 0. |
| value | numbers compared numerically, after removing thousands separators; the unit or currency must equal one of the gold forms. c = 1 or 0. |
| list | each item matched as an entity; c = F1 of the matched items against the gold items |
| short-text | the gold lists key phrases, each with forms, and a minimum count. c = 1 if at least that many appear, otherwise 0. **This is the one brittle rule:** short-text questions are reported separately, and all of them are audited (§6). |

A value that matches a **rejected candidate** (guidelines §13.3) is recorded with that candidate's reason.

#### 4.1.1 Accepted aliases
Aliases are fixed in the gold before it is frozen. The scorer only looks them up and makes no judgement of
meaning.

**Where the accepted forms of a gold value come from**, and nowhere else:
1. **The gold `value.forms`,** written by the annotators.
2. **For entity values,** the gold entity's `name` and `aliases`.
   - `aliases` holds only names and abbreviations that the documents use for that entity ("Tallis", "O&V").
   - Role references and descriptions ("the contractor", "our survey manager") are not aliases, because
     what they refer to depends on context. An annotator who wants one accepted must list it in
     `value.forms`, where adjudication can see it.

**Mechanical normalisation,** applied identically to the answer and to every form, in this order:
1. Unicode NFKC
2. remove diacritics ("Joaquín" becomes "Joaquin")
3. case-fold
4. replace "&" with "and"
5. collapse whitespace
6. trim punctuation at both ends
7. drop one leading "the "

**Numbers:**
- Thousands separators and trailing decimal zeros are removed, and numbers are compared numerically.
- The currency symbols £, € and $ are equivalent to GBP, EUR and USD.

These are string and number operations only.

**Never part of matching:**
- synonyms or paraphrases
- fuzzy or edit-distance matching
- substrings
- embeddings or language models
- any rule that depends on the question or context

**Rules for gold forms:**
- **Who adds them:** both annotators, while writing their gold. At adjudication, the adjudicated gold takes
  the forms both annotators accept. Forms they disagree on are logged as a disagreement (category: value).
- **Frozen with the gold:** forms are included in the gold's SHA-256 manifest.
- **Unambiguous:** after normalisation, no form may match two different candidate values. That includes
  the main answer, the alternatives and the rejected candidates. This is checked when the gold is frozen.
- **Correct but unmatched:** when the audit finds an answer correct but not matched, it is counted and
  reported per system (§6). A missing form may be added only by a recorded amendment before a held-out run.
  Scores already reported are never silently recomputed; if they are recomputed, both versions are
  reported.

### 4.2 Answer credit A
A = (credit from the table below) × c. Where the declared uncertainty takes no value (the `insufficient`,
`not-yet-available` and `disputed`-without-value cells), c is not applied.

| Gold status | declared `stated` or `inferred`, correct value | declared `disputed` | declared `insufficient` | declared `not-yet-available` | definite but wrong value, or `null` value with a definite declaration |
|---|---|---|---|---|---|
| `stated` | 1 | 0.3 if the correct value is among `competing`, else 0 | 0 | 0 | 0 |
| `inferred` | 1 | 0.3, as above | 0 (0.3 if the gold inference is `continuation` in the recorded frame) | 0 | 0 |
| `disputed` | 0 (one side asserted as definite) | 1 if `competing` matches every side's forms; 0.7 if it misses a side | 0.4 | 0.2 | 0 |
| `insufficient` | 0 | 0.4 | 1 | 0.5 | 0 |
| `not-yet-available` | 0 | 0.2 | 0.7 | 1 | 0 |

- **`stated` and `inferred` are treated alike for credit.** Whether a system distinguishes them is reported
  as status agreement, a diagnostic.
- **Several acceptable gold answers.** The answer is compared with:
  - the main gold answer
  - every alternative (guidelines §12.3)
  - any reading adjudicated `both-acceptable`

  The highest score counts. Alternatives give full credit: they are, by definition, defensible.
- **Questions with an `unspecified` frame.**
  - The declared `answer.frame` selects which frame's gold answers are compared.
  - If `answer.frame` is missing, the best score is taken within each frame's gold answers, and the
    **lower** of the two frames' scores counts.

### 4.3 Evidence credit e: all essential evidence for full credit
- Cited segments are the `segment` values in `evidence`; the first ten count.
- An essential item in a gold set is covered when its segment is cited.

| Situation | e |
|---|---|
| every essential item of at least one gold set is covered | 1 |
| otherwise | 0.5 × the best coverage over the sets (always below 0.5) |
| gold `disputed` | 1 if one set per side is fully covered; otherwise 0.5 × the mean over the sides of each side's best coverage |
| gold `insufficient` or `not-yet-available` | not applicable |

- **Multi-source questions** (every gold set spans two or more documents or asserting sources) are reported
  as their own subset, with the complete-evidence rate.
- A correct conclusion with one of two essential sources earns at most 0.625 (§4.4), and is flagged
  `incomplete-evidence`.
- Context items are never required.

### 4.4 Question score
- `Q = A × (0.5 + 0.5 × e)` when the compared gold answer has evidence sets
- `Q = A` when it has none

Full credit therefore needs both a correct answer with appropriate uncertainty and all the essential
evidence. A correct answer with no citations earns 0.5. Citations without a correct answer earn nothing.

### 4.5 Flags
Flags are counted, not added to Q.

| Flag | Raised when |
|---|---|
| `unsupported-certainty` | declared `stated` or `inferred`, and no gold answer with a definite status (main or alternative) matches the value |
| `confident-error` | declared `stated` or `inferred` with a wrong value, where the gold main status is definite |
| `failure-to-answer` | declared `insufficient` or `not-yet-available`, or gave a `null` value, where some gold answer is definite |
| `incomplete-evidence` | A ≥ 0.7 and e < 1 |
| `contract-failure` | §3 |
| `rejected:<reason>` | the value matches a rejected candidate |
| `status-mismatch` | diagnostic only: `stated` declared where the gold is `inferred`, or the reverse |

### 4.6 Reported per system
Counts with intervals:
- mean Q, mean A
- complete-evidence rate, overall and for multi-source questions
- each flag's rate, over the questions where it can occur
- the rejected-candidate histogram
- contract failures
- results by frame, by gold status and by answer type

Unresolvable questions are reported apart.

## 5. Worked examples
These use the guidelines' examples. Segment ids are illustrative.

| # | Gold | Contract answer (abridged) | c | A | e | Q | Flags |
|---|---|---|---|---|---|---|---|
| 1 | When did Tallis start on site? stated, 9 Feb 2026; set {seg-12feb} | value `"2026-02-09"`, stated, evidence [seg-12feb] | 1 | 1 | 1 | **1** | |
| 2 | the same | value `"2026-02-02"`, stated | 0 | 0 | – | **0** | confident-error, rejected:corrected |
| 3 | the same | value `{"from":"2026-02-01","to":"2026-03-01"}`, stated, [seg-12feb] | 0.5 | 0.5 | 1 | **0.5** | |
| 4 | Condition met? inferred, combination; one set {seg-12may, seg-20may} | `"yes"`, inferred, [seg-20may] | 1 | 1 | 0.25 | **0.625** | incomplete-evidence |
| 5 | the same | `"yes"`, stated, [seg-12may, seg-20may] | 1 | 1 | 1 | **1** | status-mismatch |
| 6 | Survey complete on 30 June? disputed; sides {seg-table} form "yes", {seg-chat} form "no" | value null, competing ["yes","no"], disputed, [seg-table, seg-chat] | – | 1 | 1 | **1** | |
| 7 | the same | `"yes"`, stated, [seg-table] | – | 0 | – | **0** | unsupported-certainty |
| 8 | Ravi at Tallis, 1 Oct (actual)? main insufficient; alternative no, inferred, set {seg-1jul} | null, insufficient | – | 1 | n/a | **1** | |
| 9 | the same | `"no"`, inferred, [seg-1jul] | 1 | 1 (via the alternative) | 1 | **1** | |
| 10 | Ravi at Tallis, 15 Jul (actual)? inferred, continuation; set {seg-1jul} | null, insufficient | – | 0 | – | **0** | failure-to-answer |
| 11 | According to the documents, Ravi at Tallis on 1 Oct? (recorded) inferred, continuation; {seg-1jul} | null, insufficient | – | 0.3 | 0 | **0.15** | failure-to-answer |
| 12 | Joaquín site lead 1 Apr? (unspecified) recorded: no, {seg-17mar}; actual: no (main), set {seg-17mar, seg-20apr}; alternative insufficient | `"no"`, inferred, frame omitted, [seg-17mar] | 1 | 1 / 1 | recorded 1, actual 0.25 | **0.625** (the lower of 1 and 0.625) | incomplete-evidence |
| 13 | the same | `"no"`, inferred, frame `"actual"`, [seg-17mar, seg-20apr] | 1 | 1 | 1 | **1** | |

Row 12 shows why declaring the frame matters. Row 4 shows that full credit needs all the essential
evidence.

## 6. Audit of explanations and evidence (separate from the score)
The deterministic score checks that the right segments were cited. It cannot check that they support the
answer, or that the explanation is true. People do, separately.

**Who:** two auditors who did not build any evaluated system. They are blind to system identity: names are
removed, and answers are shuffled across systems within each question.

**What is audited:**
- **In the trial:** every answer.
- **In M1:** for each system, a random sample fixed by a recorded seed, of at least 30 answers. It also
  includes every multi-source question and every short-text question.

**The form, for each answer:**

| # | Item | Values |
|---|---|---|
| X1 | Is the explanation consistent with the documents? | consistent / partly / inconsistent |
| X2 | Does it assert anything not in the documents? | no / yes (list) |
| X3 | For each cited segment: does it support the answer? | supports / partly / irrelevant / contradicts |
| X4 | Do the cited segments, together, support the answer? Judged on the documents, regardless of the gold sets. | yes / partly / no |
| X5 | Is the explanation consistent with the declared uncertainty (e.g. "probably" with `stated`)? | yes / no |
| X6 | Right answer for the wrong reason? | no / yes |

**Reported per system:**
- explanation-consistency rate (X1)
- unsupported-content rate (X2)
- citation-support rate (X3)
- **supported-answer rate:** deterministically correct (c = 1) **and** X4 = yes
- uncertainty-consistency rate (X5)
- right-for-the-wrong-reason count (X6)

Auditor agreement (per item) and adjudicated outcomes are reported too.

**Gold gaps.** A citation that X4 finds supporting, but which is in no gold set, is logged as a possible gold
gap. The gold is amended only by a recorded amendment before a held-out run, never to re-score a run
already made.

**What the audit changes:** it never changes Q. It is reported beside Q, so that a system that cites the
right segments for the wrong reasons is visible.

**No language model** is used in the audit.

## 7. Known limitations
- **Matching is exact.** A correct entity written in an unlisted form ("O&V" for Oskarsen & Vey) scores 0.
  Gold forms must be generous, and the audit reports such misses as gold-form gaps.
- **Date ranges:** the rule that a coarser answer earns half credit is a convention.
- **Short-text questions** depend on key phrases, so they are reported separately and always audited.
- **The contract's uncertainty labels** match the gold's own statuses. Systems that already reason in such
  categories may find it easier to fill in (bias-audit-v0.md, B17).
- **Segment-level citation** is coarse: the right email with the wrong sentence still covers the item. The
  audit's X3 and X4 measure what segment matching cannot.

## 8. Experimental secondary metric
The earlier natural-language rubric is kept as **scoring-nl-experimental-v0.md**. It is applied only to the
optional `natural_language_answer` field, and is reported separately, labelled **experimental and
potentially brittle**. It is never combined with the primary score.

## Appendix A: instructions and label definitions given to every system
> For each question, return one JSON object with the fields `question`, `answer`, `uncertainty`, `evidence`
> and `explanation`, as specified in the attached contract.
>
> Choose `uncertainty` as follows:
> - `stated`: the documents directly state the answer for the time asked.
> - `inferred`: the answer follows from the documents by reasoning, for example:
>   - combining sources
>   - date arithmetic
>   - a state continuing when the documents give good reason to think it did
>   - a list that describes itself as complete leaving something out
> - `disputed`: the documents give incompatible answers, and do not settle which is right. List them in
>   `answer.competing`.
> - `insufficient`: the documents do not establish an answer. Give `null` as the value.
> - `not-yet-available`: no document available by the question's "as of" date says anything relevant. Give
>   `null` as the value.
>
> If a question does not say whether it asks what the records show or what was actually the case, state the
> reading you answer in `answer.frame`.
>
> Cite the segments you rely on by their ids, and give a brief explanation of at most 80 words.
