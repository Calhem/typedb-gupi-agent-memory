# Independent review checklist: annotation guidelines and scoring, draft v0 (revision 2)

Date: 2026-11-03. Status: **approved for external review.** The material under review is provisional: the
guidelines are at revision 2, and the scoring protocol is not frozen.

## For the reviewer
**Who this is for.** Someone who has not worked on GUPI, or any of the systems being compared, and who is
comfortable reading careful prose about business documents. No programming knowledge is needed.

**What to read, and in what order:**
1. **guidelines-v0.md**, the annotation guidelines. Read up to §15; stop before the worked examples
   (§16).
2. **The practice task** (Part 1 below), before reading §16.
3. **guidelines-v0.md §16-§18,** then:
   - **annotation-template/README.md** (the spreadsheet template)
   - **scoring-protocol-v0.md** (the primary scoring)
   - **scoring-nl-experimental-v0.md** (the experimental secondary metric)
4. **Sections A-H** of this checklist.
5. Only then, **bias-audit-v0.md,** and section I. It is read last so that its findings do not steer yours.

**What not to read:** GUPI's code, its database schema, its design records (ADRs) or its other
documents. The review tests whether the guidelines stand on their own, without knowing the system they
will be used to evaluate.

**How to answer.** For each item, give an answer, a severity where something is wrong, and a comment.
- **Answers:**
  - `yes`
  - `partly`
  - `no`
  - `n/a`
- **Severities:**
  - **blocking:** the trial should not start until it is fixed
  - **major:** it would distort annotations or scores
  - **minor:** wording, or a nice-to-have

Concrete suggestions are more useful than verdicts.

**Time:** about 3-5 hours. Please log it, roughly by part.

**Declare:** any connection to GUPI, TypeDB, the owner, or to any compared system or vendor. A connection
does not disqualify you, but it is reported.

**Return:** a filled copy of this file, your practice annotations and your time log.

## Part 1: practice task (before reading §16)
1. In guidelines-v0.md §16, read only the quoted passages (the lines starting with ">") of Examples 3, 4, 5
   7 and 8. Do not read the explanations below them.
2. For each passage, write down in plain words, or in the format of §15 if you prefer:
   - the statements
   - their attribution and certainty
   - any negation, termination or reinstatement
   - each statement's evidence standing (§8.1), and why
   - your answers, statuses and evidence for these questions:
     - **Example 3:** As of 5 May, could the Authority have known that Joaquín planned to leave?
     - **Example 4:** According to the records, was Joaquín site lead on 1 April? And was he actually site
       lead on 1 April?
     - **Example 5:** When did Tallis start on site? Was the soil survey complete on 30 June?
     - **Example 7:** Was Ravi actually working for Tallis on 1 October? And on 15 July?
     - **Example 8:** Was Ravi working for Tallis as survey staff on 1 October? Which of the three items
       support your answer, and which do not?
3. Then read §16 and list every difference between your answers and the guidelines'. For each, say who you
   think is right and why.

The differences are the most useful evidence of whether the guidelines can be applied consistently.

## A. Neutrality
| # | Item | Answer | Severity | Comment |
|---|---|---|---|---|
| A1 | Do any categories, field names or explanations presuppose a particular kind of software (a database, a graph, a knowledge base, a rule engine)? | | | |
| A2 | Could a careful person who stores nothing, and just reads the documents, produce every answer the gold asks for? | | | |
| A3 | Are any distinctions there because a system would make them, rather than because a careful human reader would? | | | |
| A4 | Do the worked examples favour facts that are easy to put in a table or graph, over facts that live in prose (reasons, tone, caveats)? | | | |
| A5 | Does the annotation format (§15) favour any way of storing data? | | | |
| A6 | Does the guidelines' vocabulary sound like any particular product, or like software documentation rather than reading guidance? | | | |

## B. Can the guidelines be applied consistently?
| # | Item | Answer | Severity | Comment |
|---|---|---|---|---|
| B1 | For each distinction below, would two careful annotators usually agree? Rate each high, medium or low, and say why. | | | |
| B1a | stated, implied, or the annotator's inference (§6) | | | |
| B1b | commitment: certain, probable, possible, unknown (§6) | | | |
| B1c | update, correction, or contradiction (§11) | | | |
| B1d | negation, termination, or reinstatement (§10) | | | |
| B1e | recorded, actual, or unspecified frame (§12.1) | | | |
| B1f | when to add an alternative, versus when to lower confidence (§12.3) | | | |
| B1g | `insufficient` versus `not-yet-available` (§12.2) | | | |
| B1h | essential evidence versus context (§13.1) | | | |
| B1i | where one statement ends and the next begins (§4) | | | |
| B1j | the time range for vague phrases ("late May", "end of the month") (§7.1) | | | |
| B2 | Is there a case the guidelines give no rule for? List it. | | | |
| B3 | Do any two rules contradict each other? | | | |
| B4 | From your practice task: how many of your answers differed from the guidelines' examples, and were the guidelines right? | | | |
| B5 | Is any instruction too long or too subtle to follow consistently under time pressure? | | | |

## C. Ambiguous examples
For each, say whether you agree with the guidelines' treatment, what you would record instead, and whether
the guidelines should change.

| # | Item | Answer | Severity | Comment |
|---|---|---|---|---|
| C1 | Example 4: for "actually site lead on 1 April", the main answer is now "no" (weighed on evidence) and the alternative is `insufficient`. Is the weighing right? Is keeping both right, or should one be the only answer? | | | |
| C2 | Example 2: "the end of July" is taken as its last week. Is that convention reasonable? | | | |
| C3 | Example 5: the status table and the chat are treated as an unresolved dispute. Would a reasonable reader prefer one, and should the guidelines allow that? | | | |
| C4 | Example 7: two weeks after an employer-announced departure the actual answer is "no"; three months later it is `insufficient`, with "no" as an alternative. Is the weighing of standing, scope and timing (§12.4) sensible? Would you draw the line elsewhere? | | | |
| C5 | Example 1: an approval "provided Tallis completes the survey first" is recorded as a conditional decision. Was anything approved yet, in your reading? | | | |
| C6 | Example 3: Joaquín's reported plan has commitment `unknown`. Is that right for "Joaquín told me he's leaving"? | | | |
| C7 | Example 6: the condition being met is `inferred` (combination), not `stated`. Agree? | | | |
| C8 | Is there an example you found misleading, or a common situation with no example? | | | |
| C9 | Example 8: the register is authoritative (complete, current, issued by the employer), the attendance list is not, and the rumour is unverified. Do you agree with each standing, and with how the rumour is weighed? | | | |

## D. Missing phenomena
For each, mark one of:
- **covered:** the guidelines say what to do
- **partly**
- **not covered**
- **not needed** in project documents

Add any others you think of.

| # | Phenomenon | Answer | Severity | Comment |
|---|---|---|---|---|
| D1 | Quantities, units, money and currency | | | |
| D2 | Acting, temporary and deputy roles ("acting site lead", "covering for Hana") | | | |
| D3 | Delegation and authority ("signed for the director") | | | |
| D4 | Changes to organisations (renaming, mergers, reorganisations, team splits) | | | |
| D5 | One person with several names; two people with the same name | | | |
| D6 | Document versions, drafts and superseded attachments | | | |
| D7 | Retroactive changes ("with effect from" a date already past) | | | |
| D8 | Recurring events ("every Monday", "monthly report") | | | |
| D9 | Partial completion and percentages ("80% complete") | | | |
| D10 | Cancelled or postponed events that never happened | | | |
| D11 | Vague participants ("someone from Tallis", "the team") | | | |
| D12 | Implicit negation ("failed to deliver", "missed the deadline") and double negation | | | |
| D13 | Quantifiers ("all subcontractors", "none of the reports") | | | |
| D14 | Counterfactuals ("had the survey been done, we would have ...") | | | |
| D15 | Sarcasm, jokes and irony in chat | | | |
| D16 | Deliberate misinformation, or a source contradicting itself | | | |
| D17 | Missing or redacted material ("see attached", with no attachment) | | | |
| D18 | Time zones, and dates near midnight | | | |
| D19 | Attribution more than two levels deep | | | |
| D20 | Abbreviations and project jargon | | | |
| D21 | Others (list) | | | |

## E. Recorded knowledge versus actual conditions; ambiguity
| # | Item | Answer | Severity | Comment |
|---|---|---|---|---|
| E1 | Is the difference between the `recorded` and `actual` frames clear enough to apply? | | | |
| E2 | Will authors write questions whose frame is clear? Should `unspecified` be allowed at all? | | | |
| E3 | Does the guidelines' rule, that the absence of a recorded change never establishes the actual state, match how you would answer? | | | |
| E4 | Could the alternatives mechanism be abused, so that too many answers count as acceptable? | | | |
| E5 | Are the ambiguity types (`wording`, `evidence`, `frame`) enough, and distinguishable? | | | |
| E6 | Can the five evidence standings (§8.1) be told apart consistently? Which pairs are most often confused? | | | |
| E7 | Is "document type alone never establishes authority" workable? Do the guidelines say clearly enough what does establish it? | | | |
| E8 | Will two annotators weigh standing, scope and timing (§12.4) similarly, or is the procedure too open? What would make it more consistent without becoming a blanket rule? | | | |

## F. Scoring
| # | Item | Answer | Severity | Comment |
|---|---|---|---|---|
| F1 | Does the answer contract (scoring-protocol §2) let every kind of system express its answer fairly, including a person or a text reader? Is anything missing or unnecessary? | | | |
| F2 | Is validation and scoring of the structured fields fully deterministic (§3, §4)? Name any step that needs judgement. | | | |
| F3 | Are the credit values (§4.2) sensible? In particular: 0.3 for abstaining when the records decide; 0.4 for `insufficient` against a dispute; 0 for certainty where the gold is uncertain; equal credit for `stated` and `inferred`. | | | |
| F4 | Do you agree that full credit needs all essential evidence, so that a correct conclusion with one of two required sources stops at 0.625 (§4.3)? | | | |
| F5 | Are the label definitions given to systems (Appendix A) clear, and neutral between kinds of system? | | | |
| F6 | Can the protocol be gamed? For example: always answering `insufficient`, citing ten segments, or omitting the frame. Estimate what "always `insufficient`" would score. | | | |
| F7 | Is exact matching against gold forms (§4.1) fair? Will gold authors list enough forms? | | | |
| F8 | Is scoring an answer with no declared frame against the less favourable reading fair? | | | |
| F9 | Is the audit of explanations and evidence (§6, items X1-X6) adequate to catch answers that cite the right segments for the wrong reasons? Is blinding enough? | | | |
| F10 | Is the experimental natural-language metric (scoring-nl-experimental-v0.md) clearly enough labelled as secondary and potentially brittle? Should it be kept at all? | | | |

## G. Workload and clarity
| # | Item | Answer | Severity | Comment |
|---|---|---|---|---|
| G1 | How long did it take to read the guidelines well enough to annotate? | | | |
| G2 | Which terms were unclear or needed a definition? | | | |
| G3 | Is the spreadsheet template (annotation-template/) usable? Are its conventions (lists with `;`, spans as `start-end`, child sheets) and its conversion rules clear? | | | |
| G4 | Are there enough worked examples? Which would you add? | | | |

## H. Overall
| # | Item | Answer | Comment |
|---|---|---|---|
| H1 | Are the guidelines ready for the two-document trial? (`yes`, `with changes`, `no`) | | |
| H2 | Your three most important changes | | |
| H3 | Anything that should be decided by the owner rather than by annotators | | |

## I. The bias audit (read last)
| # | Item | Answer | Severity | Comment |
|---|---|---|---|---|
| I1 | Did your sections A and F find tilts that the audit missed? | | | |
| I2 | Do you disagree with any finding, or with its severity? | | | |
| I3 | Are its mitigations adequate? | | | |
