# Annotation guidelines, draft v0 (two-document trial)

Date: 2026-11-03. Status: **draft v0, revision 2. Provisional; approved for external review, not approved for
freezing.**
- **Scope:** these guidelines are for the two-document trial only (README.md in this folder).
- **Changes:** they are expected to change after the trial, and are frozen only before the eight-document
  mini-pilot.
- **Companion documents:**
  - bias-audit-v0.md: the bias audit
  - scoring-protocol-v0.md: how answers are scored (primary: a common structured answer contract)
  - scoring-nl-experimental-v0.md: an experimental secondary metric for free-text answers
  - review-checklist-v0.md: the checklist for an independent reviewer

**Revision 1 (after the owner's first review):**
- Questions now state whether they ask about recorded knowledge or about actual conditions (§12.1).
- Legitimate ambiguity is kept in the gold as alternatives (§12.3).
- Continuation is limited to questions about recorded knowledge (§13.2).
- Evidence sets separate essential items from context (§13.1).
- Example 4 is revised, and Example 7 is new.

**Revision 2 (after the owner's second review):**
- The blanket rule that actual-frame questions stay `insufficient` after a recorded termination is
  replaced. Statements now record their evidence standing (§8.1), and an actual-frame conclusion is reached
  by weighing standing, scope and timing (§12.4).
- Document type alone never establishes authority.
- A new inference, `closed-list`, is added.
- Examples 4 and 7 are revised, and Example 8 is new.

## 0. About these guidelines
**Who they are for:** the people who write and annotate the trial's documents, questions and answers. You
need no knowledge of any software system, and you should not consult one.

**What they are independent of.** They describe how to read business documents carefully: who says what,
about whom, about when, and how sure anyone can be. They are deliberately independent of every system
being evaluated.
- The categories come from the documents' own domain and from published annotation practice that predates
  this project:
  - time and event annotation in the style of TimeML
  - the source-and-certainty ("factuality") distinctions of FactBank
  - the verdict labels used in fact-checking datasets such as FEVER and AVeriTeC
  - entity, relation and event annotation in the style of ACE/ERE
- They borrow ideas, not those schemes' exact labels, and they do not claim conformance with any of them.

**The one rule that matters most:** keep apart three things that are easy to blur.
1. **What a source states:** the words on the page, attributed to the person who said them.
2. **What the text implies:** what a competent reader takes the source to be committed to without it being
   said outright.
3. **What you, the annotator, believe happened:** your judgement, which may weigh several sources, and which
   you label as yours.

Layer 1 and 2 annotations never contain your judgement. Layer 3 annotations always say what they are based
on.

## 1. General principles
1. **Annotate what the documents support.** Use ordinary common sense (a person cannot be in two offices
   at once; "next Monday" means the Monday after the message was written). Do not use outside knowledge of
   real organisations.
2. **Record a source's statement even when you think it is wrong.** Its errors are data. Record your
   disagreement in the judgement layer (§9), not by editing the statement.
3. **Silence is not denial.** That a document does not mention something never means it did not happen.
   Only an explicit statement is a negation (§10).
   - **What is recorded is not the same as what happened.** That no reinstatement, correction or change was
     recorded tells you what the records show. It does not establish what happened in reality (§12.1).
4. **Do not upgrade certainty.** "I think", "probably", "apparently" and "rumour has it" stay hedged.
   Never strengthen a hedged statement because it turned out to be true elsewhere.
5. **Do not force a decision.** When evidence is ambiguous, conflicting or missing, say so with the
   statuses in §12. Recording two readings is better than choosing one.
6. **Prefer the less definite option when in doubt,** and add a note explaining the doubt.
7. **Every annotation that is not verbatim needs a reason:** an inference, a resolved reference, a
   normalised date. Write it in `note`.
8. **Work alone until the freeze** (README.md, Procedure). Do not discuss the documents with the other
   annotator before both annotations are frozen.

## 2. What you produce
For each document, one annotation file. For the questions, one answer file per annotator. The format is
in §15. The record types are:

| Record | Layer | Purpose |
|---|---|---|
| `document`, `segment` | source | the document and its parts (messages in a thread, sections of minutes), with authors and dates |
| `entity`, `mention` | source | the people, organisations and things referred to, and each place they are mentioned |
| `time` | source | each time expression, verbatim, with its normalised meaning |
| `statement` | source | one thing a source states or implies, with its participants, time, polarity, certainty and attribution |
| `link` | source or judgement | how two statements relate: corroborate, contradict, correct, update, and so on |
| `judgement` | annotator | what you believe happened, based on named statements |
| `question`, `answer` | annotator | the trial questions and each annotator's answer, status and evidence |
| `adjudication` | both | the outcome of each disagreement (§14) |

**The layers have different purposes.**
- The source layer (statements, mentions, times, links) is used to measure agreement between annotators,
  and to diagnose errors.
- Systems are compared on their **answers and evidence** only (§12, §13), never on whether they reproduce
  the statement records. A system that keeps no records at all can still score perfectly. (Bias audit B2.)

## 3. Entities, mentions and references
**Entities** are the people, organisations, teams, projects, deliverables, documents, sites and other
things the documents talk about.
- Create one `entity` per distinct thing. Give it a `kind` (person, organisation, team, project,
  deliverable, document, site, other) and a `name`: the fullest name used in the documents.
- List other names it goes by as `aliases`.
- Entity ids are your own. The two annotators' ids are matched at adjudication through the mentions, so
  they need not agree.

**Mentions.** Each reference in the text becomes a `mention`: its exact text and character offsets, and
the entity it refers to.
- Record the kind of reference:

  | Reference | Example |
  |---|---|
  | `name` | "Ravi Lindqvist" |
  | `pronoun` | "she", "they" |
  | `role-reference` | "the site lead", "our survey manager" |
  | `description` | "the person who chaired Tuesday's meeting" |

- Record how the reference was resolved:
  - **`stated`:** the text makes it unambiguous.
  - **`inferred`:** you worked it out; say how in `note`.
  - **`unresolved`:** you cannot tell. Create a placeholder entity ("unidentified person referred to as
    'the new auditor'"), and never guess.

**Role references are time-sensitive.** "The site lead" refers to whoever held that role when the sentence
was written, not today. Resolve it at the segment's date, and mark it `inferred` unless the text names the
person.

**Groups.** "The board" is an entity (kind `team`). Its members are only linked to it if a document says so.

## 4. Statements, participants and roles
A **statement** is one thing a source says about the world. Split a sentence into several statements only
where it makes several separable assertions: "Hana chaired the meeting and approved the minutes" is two
statements.

Each statement records:
- **`kind`:**
  - `state`: something that holds over a period: a role, a responsibility, a membership, a status
  - `event`: something that happens: a meeting, an appointment, a resignation, a delivery
  - `decision`: an event in which someone decides something
  - `obligation`: something someone must do, usually by a time
  - `other`: anything that fits none of these; describe it in `note`
- **`description`:** a short, faithful paraphrase in plain English. It adds nothing the source does not say.
- **`predicate_text`:** the relationship or event in the source's own words ("took over as", "signed off").
- **`participants`:** every thing that takes part, each with a **role** describing how it takes part.
  - Use the role names in the table below where they fit. Where none fits, write your own short role name
    in plain English, and note it.
  - A statement may have any number of participants. Keep a participant even if the source mentions it only
    in passing (for example "on behalf of the Authority").
  - A participant can be an entity, a time, a literal value (an amount, a quantity, a status word), or
    another statement. A statement as participant is used for conditions, and for the content of a
    decision or request.

| Suggested role | Meaning |
|---|---|
| `holder` | who a state is about (the person who holds a role) |
| `position` | the role, post or responsibility held |
| `organisation` | the organisation within which a state or event applies |
| `project` | the project it concerns |
| `actor` | who does something in an event |
| `decider` | who makes a decision |
| `on-behalf-of` | whom an actor or decider represents |
| `approver` | who approves |
| `object` | what is acted on, decided, delivered or approved |
| `recipient` | who receives something |
| `obligated-party` | who must do something |
| `action` | what must be done (a short phrase, or a statement) |
| `condition` | a statement that must hold for this one to apply |
| `amount` | a quantity, price or count, with its unit as written |
| `reason` | why, in the source's words (keep it, even if no question needs it) |

**Keep detail that does not fit.** Reasons, nuances, tone and qualifications that have no natural role
still belong in `description` or `note`. Never drop text because it is hard to structure. The bias audit
(bias-audit-v0.md, B3) explains why.

## 5. Events, decisions, obligations and changing responsibilities
- **Events** have an event time (§7). A decision is an event: record who decided, what was decided, on
  whose behalf, and under what condition.
- **The effect of a decision is a separate statement.**
  - "The board approved the transfer of site responsibility to Oskarsen & Vey with effect from 1 June" is a
    `decision` (the approval, on its date), plus a `state` (Oskarsen & Vey responsible for the site, from
    1 June).
  - Mark the state `implied`: the decision implies it, but no source reports it as having happened.
- **Obligations** record the `obligated-party`, the `action`, the due time if any, and who imposed the
  obligation if stated.
  - A later statement may move the due date (a `link` of type `updates`, §11), fulfil it (`fulfils`) or
    cancel it (`cancels`).
  - Fulfilling an obligation late is recorded as a fulfilment with its own event time. It is not a
    contradiction of the due date.
- **Changing responsibilities** are states with a start and an end (§7.3). A handover is usually two
  states: the old holder's ending and the new holder's starting. They may be in one sentence or several
  documents.
- **Plans and intentions** ("we intend to appoint", "Joaquín will take over in May") are statements with
  modality `planned` (§6). They are never recorded as having happened.

## 6. Stated, implied and inferred; certainty and modality
**How the source conveys it.** Each statement has `conveyed`:
- **`stated`:** the source says it in so many words.
- **`implied`:** the source does not say it outright, but is clearly committed to it. Examples:
  - "now that Joaquín is back on site" implies Joaquín returned
  - "Hana is no longer the safety adviser" implies she was before
  - an approval "with effect from 1 June" implies the state from 1 June

  Mark `implied` only when a competent reader would agree that the source is committed to it. Otherwise it
  is your inference, and belongs in a judgement (§9).

**How strongly the source commits.** Each statement has `commitment`, which is about the source, not
about you:

| Value | Typical wording |
|---|---|
| `certain` | plain assertion: "Ravi delivered the report on 2 July" |
| `probable` | "should", "expected to", "I believe", "likely" |
| `possible` | "may", "might", "could", "it's possible that" |
| `unknown` | the source reports it without committing: "Ravi says ..." in a neutral relay |

**What kind of claim it is.** Each statement has `modality`:

| Value | Meaning |
|---|---|
| `actual` | it is happening, happened or holds |
| `planned` | intended or scheduled |
| `required` | an obligation |
| `permitted` | allowed |
| `requested` | asked for |
| `conditional` | holds only if a condition holds; link the condition |
| `hypothetical` | "if we lost the crane ..." |
| `question` | asked, not asserted |

Hedges and modality are independent. "The survey should be finished by Friday" is `planned` with
commitment `probable`.

## 7. Time
Three different times can matter for one statement. Record each separately; never merge them.

| Time | Question it answers | Where it is recorded |
|---|---|---|
| **Event time** | when something happened | `event_time` on an event or decision |
| **Validity time** | over which period a state held | `holds_from`, `holds_until`, `holds_at` on a state |
| **Availability time** | when the information reached the reader | `written` and `available_from` on the segment |

**Example:** "At its meeting on 12 May, the board approved, with effect from 1 June, the transfer of site
responsibility". The minutes were circulated on 15 May.
- The approval's event time is 12 May.
- The responsibility's validity starts on 1 June.
- The information was available from 15 May.

### 7.1 Time expressions
Record every time expression as a `time` record:
- **`text`:** verbatim, with its offsets.
- **`value`:** a range written as `from` (inclusive) and `to` (exclusive), ISO 8601 dates, meaning "the
  moment lies somewhere in this range".
  - "In June 2026" is `{from: 2026-06-01, to: 2026-07-01}`.
  - "On 3 March 2026" is `{from: 2026-03-03, to: 2026-03-04}`.
  - "Late May" is `{from: 2026-05-21, to: 2026-06-01}`, with a note: approximate words get a reasonable
    range and a note.
- **`granularity`:** day, week, month, quarter, year or other.
- **`anchor`:** how you got the value:
  - **`explicit`:** fully specified in the text ("3 March 2026").
  - **`document-date`:** relative to the segment's date ("yesterday", "next Monday", "in June" written in
    April). Say how in `note`.
  - **`other-time`:** relative to another time expression ("two weeks after the survey"). Name it.
  - **`inferred`:** worked out by wider reasoning. Explain it.
  - **`unresolvable`:** you cannot pin it down. Give the widest honest range, or leave `value` empty.
- **A month or weekday without a year or date:** resolve it from the tense and the document's date. "The
  report is due in June", written in April 2026, is June 2026. If the tense does not settle it ("June was
  mentioned"), mark the anchor `unresolvable` and do not guess a year.

### 7.2 Event time
For an event, `event_time` is a time record. If the event's time is not given, leave it empty and note
anything the text implies, such as "before the email of 20 April".

### 7.3 Validity time of states
A state can have, each optional:
- **`holds_from`:** when it started, as a time range ("Joaquín has led the site since January" gives
  `holds_from` in January).
- **`holds_until`:** when it ended, as a time range.
- **`holds_at`:** moments at which the source says it held: "currently", "still", "as of today", or a dated
  status report. Use the segment's date for "currently".

Rules:
- **An unstated start or end is unknown, not "always" or "still".** "Joaquín is site lead" in a 3 March
  email gives `holds_at` 3 March only, with no start and no end.
- **"Still" gives a `holds_at`,** and implies an earlier start whose time is not stated. It never extends
  the state forward.
- **A planned end** ("Joaquín will hand over at the end of the month") is a separate `planned` statement.
  It is not a `holds_until`.

### 7.4 Availability time
- Each segment has a `written` time and an `available_from` time.
  - Email: the sending time, for its recipients.
  - Minutes: the circulation date if stated, otherwise the meeting date, noted.
  - A status table: its "as of" date.
- **Quoted or forwarded material** keeps its original `written` time. It becomes available to the forward's
  recipients at the forward's time (§8).
- Questions "as of" a date may use only segments available by then (§12).

## 8. Source attribution, hearsay and forwarded information
Every statement says **whose** assertion it is (`asserted_by`) and **how it reached the document**
(`attribution`):

| Attribution | Meaning | Example |
|---|---|---|
| `direct` | the segment's author asserts it | Ravi writes: "We finished the boreholes on Friday." |
| `reported` | the author reports, in their own words, someone else's assertion | "Joaquín told me he is leaving the project." |
| `quoted` | the author quotes someone verbatim | "Mirela's note said: 'approval is conditional on the survey'." |
| `forwarded` | it appears in forwarded or quoted earlier messages | the text below "---- Forwarded message ----" |
| `rumour` | unattributed hearsay | "I hear the crane contract has fallen through." |
| `unattributed` | stated with no clear source, e.g. an unsigned status table | |

- **Chains:** `via` lists the people it passed through, nearest first. "Wen forwarded Ravi's email, in
  which Ravi reported that Joaquín said he was leaving" gives:
  - `asserted_by` Joaquín
  - `via` [Ravi, Wen]
  - `attribution` `reported`, inside a `forwarded` segment
- **Repeated material is not corroboration.** Text quoted again in a reply, or forwarded, is the same
  assertion, not a new one.
  - Annotate it once, where it originally appears.
  - If the original is not in the documents, annotate it where it first appears.
  - Record later repetitions as `link` type `repeats`. Repetitions never count as corroboration.
- **The author's own stance** towards a report ("Joaquín says he is leaving, which I doubt") is a separate
  statement by the author, `direct`, linked with `contradicts` or `doubts`.

### 8.1 Evidence standing
Attribution says how a statement reached the document. **Standing** says what kind of evidence it is about
the world. Each statement records a `standing`, and a one-line `standing_reason`.

| Standing | Use when | Example |
|---|---|---|
| `authoritative-record` | the source is **shown by the documents** to be responsible for keeping this kind of fact, and the record covers the entity and the time in question | Tallis's own office announcing that a Tallis employee has left; a staff list the documents describe as the contractor's official, current register |
| `direct-observation` | the source reports what it saw, did or experienced itself, at or near the time | "I met Joaquín on site this morning"; "we finished the boreholes on Friday" |
| `reported` | a second-hand account: someone reports what another person said or did | "Joaquín told me he is leaving"; minutes recording a departure announced by someone else |
| `plan` | an intention, schedule or announcement of something not yet happened | "Joaquín is back as site lead from next Monday" (before Monday) |
| `unverified` | a rumour, an unattributed claim, a hedged (`possible`) statement, or a claim the documents give no basis for | "I hear Ravi's back at Tallis" |

Rules:
- **Document type alone never establishes authority.**
  - A register, table, official-looking memo or the minutes are not authoritative just because of what they
    are.
  - Authority needs a reason **from the documents**:
    - the source's stated responsibility (the employer for employment, the board for its own decisions)
    - a document describing itself as the official or current record for that scope
    - an established practice described in the documents
  - Write the reason in `standing_reason`. Without one, the standing is at most `reported` or
    `direct-observation`.
- **Authority has a scope.** A record is authoritative only for what it is responsible for. The
  contractor's register is authoritative for who the contractor employs, not for who sat on the Authority's
  board.
- **Authority has a date.** A record is authoritative as of its own date. Its standing for later times
  weakens with the gap, unless the documents show it is kept current.
- **Standing is not truth.** An authoritative record can be wrong, and a correction can overturn it (§11).
  Standing describes the evidence, not the outcome.
- **When unsure between two standings,** choose the weaker one and give `confidence: medium`.

## 9. Judgements: what you believe happened
A `judgement` records your view of what actually happened, held or was the case. It is **yours**, and it
must say what it rests on.
- **`about`:** a short description, and the same participants and times as a statement.
- **`belief`:**
  - `happened`: or held
  - `did-not-happen`: or did not hold
  - `uncertain`
  - `sources-disagree`
- **`based_on`:** the statement ids it rests on, and the statements against it.
- **`reasoning`:**
  - **`taken-from-source`:** a single statement settles it, and you have no reason to doubt it.
  - **`inferred`:** you combined or extended evidence. Give the `inference` type (§13.2) and explain it in
    one or two sentences.
- **`confidence`:** see §14.3.

Write judgements only where a question needs them, or where your reading differs from what a source
states. Judgements are not required for every statement.

## 10. Explicit negation, termination and reinstatement
These are three different things. Do not convert one into another.

| Phenomenon | What it is | How to record it |
|---|---|---|
| **Explicit negation** | the source says something does not hold or did not happen: "Hana is not the safety adviser for the quay works" | a `statement` with `polarity: negated`, covering only the time the source speaks about (its `holds_at`, or the period it states). It has no end date, and implies no start. |
| **Termination** | the source says a state ended, or reports the event that ended it: "Joaquín stepped down as site lead on 10 March" | an `event` (the stepping down, with its event time), plus `holds_until` on the state if the source gives or implies it. The state itself stays `affirmed`. |
| **Reinstatement** | a state of the same kind starts again after it ended: "Joaquín is back as site lead from Monday" | a **new** `state` with its own `holds_from`, linked to the earlier one with `link` type `resumes`. It does not cancel the termination. |

Rules:
- **"No longer"** ("Hana is no longer the safety adviser", written 3 March) carries two statements, both
  from the source:
  - a negation at 3 March, `stated`
  - an end of the earlier state at an unstated time before 3 March, `implied`
- **A negation covers only what it says.** "Not the safety adviser as of 3 March" says nothing about
  April.
- **A termination says the state ended. It does not say the state never resumed.** Whether it was still
  over on a later date is a judgement (§9) or an answer with status `inferred` (§12), never a statement.
- **A correction is different from a reinstatement.** "Joaquín never actually stepped down; the minutes
  were wrong" corrects the termination (§11). It is not a reinstatement.
- **Denials of events** ("the board did not approve the design on 12 May") are negated `event` statements.
  They cover only the stated event and time.

## 11. Contradictions, corrections, updates and uncertainty
Relate statements with `link` records. Each link has a `type`, a direction (`from` the later or newer
statement, `to` the earlier or other one), `marked` and a confidence.
- **`marked`:**
  - **`stated`:** the text marks the relation ("Correction:", "as I said", "contrary to the minutes").
  - **`inferred`:** you judged it.

| Type | Meaning |
|---|---|
| `corroborates` | an independent source states the same thing (not a repetition, §8) |
| `contradicts` | the two cannot both be true, and neither acknowledges the other |
| `corrects` | the later statement says the earlier one was **wrong**: the world did not change, the report did |
| `retracts` | a source withdraws its own earlier statement without replacing it |
| `updates` | the **world changed**: a later state or decision replaces an earlier one that was true when said (a moved deadline, a new holder) |
| `refines` | compatible but more precise ("in March" refined by "on 9 March") |
| `repeats` | quoted or forwarded copy of the same assertion (§8) |
| `resumes` | a state starting again after it ended (§10) |
| `fulfils`, `cancels` | an event that fulfils or cancels an obligation (§5) |
| `depends-on` | a statement's condition (§4) |
| `doubts` | a source expresses doubt about another statement, without contradicting it |

**Correction or update?** Ask: was the earlier statement true when it was made?
- If yes, and things then changed, it is an **update**: "the survey report is now due at the end of July"
  updates "due in June".
- If no, it is a **correction**: "we started on 9 February, not 2 February".
- If the text does not say and you cannot tell, use `contradicts`, with a note.

**Uncertainty.** Keep two kinds apart:
- **The source's uncertainty** is its `commitment` (§6). It is part of the statement.
- **Your uncertainty** about your reading is your `confidence` (§14.3).

A confidently written statement you doubt keeps `commitment: certain`. Your doubt goes into a judgement or a
note.

## 12. Questions and answers
The primary author writes the questions (README.md, Scope). Both annotators answer them independently.

**Each `question` states:**
- **`text`:** the question as a person would ask it.
- **`answer_type`:** yes-no, entity, list, date, value or short-text.
- **`about_time`:** when the question is about. This is either a moment ("on 1 April 2026"), or a period
  with a mode:
  - **`throughout`:** the whole period
  - **`at-some-time`:** at any moment within it
- **`as_of`:** the knowledge date. The answer may use only segments available by then. If absent, use all
  documents.
- **`frame`:** whether the question asks about recorded knowledge or about actual conditions (§12.1).

### 12.1 Recorded knowledge versus actual conditions
A question can ask two different things, and the gold must say which.

| Frame | Asks | Typical wording | What can answer it |
|---|---|---|---|
| `recorded` | what the records show, or had shown by the `as_of` date | "According to the project records ...", "What had been reported about ...", "Was ... recorded as ..." | what the documents state, and what follows from them, including the last recorded state persisting until a recorded change (`continuation`, §13.2) |
| `actual` | what was actually the case in the world | "Was Joaquín actually site lead on 1 April?" | evidence whose standing, scope and timing justify a conclusion about that time (§12.4). The mere absence of a recorded change does not establish the actual state, but evidence of sufficient reliability and scope may. |
| `unspecified` | the wording does not make the frame clear | "Was Joaquín site lead on 1 April?" | both readings are annotated (§12.2), and both are acceptable |

Rules:
- **A recorded-knowledge answer is not a claim about the world.**
  - "The records show he stepped down on 10 March, and no return before 27 April is recorded" is a
    complete, correct recorded-frame answer.
  - Whether the same facts also answer the actual-frame question depends on the evidence's standing, scope
    and timing (§12.4). When they do not, the answer is `insufficient`, and the recorded state goes in the
    answer's `explanation`.
- **Authors should prefer clear wording** (`recorded` or `actual`). They keep `unspecified` only where an
  everyday question would naturally be asked that way, which is useful for testing how systems qualify
  their answers.
- **The statuses mean the same in both frames,** but what counts as support differs.
  - `stated` in the recorded frame means the records state it.
  - `stated` in the actual frame means a source asserts it, with commitment `certain` or `probable`, about
    the time asked.
  - A `continuation` inference always supports recorded-frame answers. It supports an actual-frame answer
    only when §12.4 justifies it.

### 12.2 Each `answer` records
An annotator writes one answer per frame the question asks about. For `unspecified` questions, that means
two answers: one `recorded` and one `actual`.
- **`frame`:** `recorded` or `actual`.
- **`value`:** the answer, as text and, where it is an entity, the entity id. For a yes-no question,
  `yes` or `no`. Leave it empty when the status is `insufficient` or `not-yet-available`.
  - **`value.forms`:** the accepted surface forms, used by the scorer to recognise the value: names and
    aliases, and date formats.
- **`status`:** how well the documents support the value in this frame. Choose exactly one:

| Status | Use when |
|---|---|
| `stated` | at least one available source states (or clearly implies, §6) the value for the time asked, with commitment `certain` or `probable`; and no available source states otherwise, unless an explicit correction or later update settles it |
| `inferred` | no source states it for the time asked, but it follows from stated material by one or more named reasoning steps allowed in this frame (§13.2); and no available source states otherwise |
| `disputed` | available sources state incompatible values, and nothing in the documents settles which is right |
| `insufficient` | relevant material is available, but it does not support any value in this frame: only silence, only hedged (`possible`) or `unverified` statements, evidence that stops short of the time asked, or (actual frame) evidence whose standing, scope or timing does not justify a conclusion (§12.4) |
| `not-yet-available` | as of the knowledge date, no available segment says anything relevant, although later documents do |

- **`inference`:** required when the status is `inferred`.
- **`evidence`:** see §13.
- **`rejected_candidates`:** values a careless reader might give, each with the reason it is wrong (§13.3).
- **`annotator_view`:** optional. What you personally think most likely, and why, when it differs from what
  the status allows. For example, the status is `disputed`, but you lean towards the later email. This is
  where your belief goes; it never changes the status.
- **`confidence`:** see §14.3.
- **`question_problem`:** set it if the question itself is ambiguous or rests on a false assumption. Say
  why, and answer the most reasonable reading.
- **`alternatives`** and **`ambiguity`:** see §12.3.
- **`justification`:** required for an actual-frame answer reached under §12.4. It is one or two sentences
  naming the evidence's standing, its scope and the time gap, and why together they justify, or fail to
  justify, the conclusion.

### 12.3 Preserving legitimate ambiguity
Some questions have more than one defensible answer under these guidelines. The gold keeps them; it does
not pick one.
- **`ambiguity`:**

  | Value | Meaning |
  |---|---|
  | `none` | one defensible answer |
  | `wording` | the question can reasonably be read in two ways |
  | `evidence` | the documents reasonably support more than one reading |
  | `frame` | the frame is unspecified, and the two frames give different answers |

- **`alternatives`:** other defensible answers, each with a value, a status, any inference, and a sentence
  saying why it is defensible.
  - The main answer is the one the annotator finds best supported.
  - Alternatives are not wrong answers; rejected candidates are (§13.3).
- **When to add an alternative.** Ask: would a careful reader who follows these guidelines give it, and
  could you not show them to be wrong from the documents? If so, add it. If you are merely unsure of your
  own reading, use `confidence` instead.
- **At adjudication,** the outcome `both-acceptable` (§14.2) turns the second annotator's answer into an
  alternative.

**Rules:**
- A `no` needs either an explicit negation, or a reasoned inference whose type you name. Silence alone
  gives `insufficient`.
- Never resolve a dispute by your own view of which source is more credible. A document that itself settles
  it counts, for example "the contractor's register is the official record" or a later explicit correction.
  Your preference goes in `annotator_view`.
- An answer resting on a plan ("was the survey delivered by 30 June?", when only a plan to deliver by then
  is stated) is `insufficient`, with the plan listed as a rejected candidate's reason.

### 12.4 Reaching an actual-world conclusion
An actual-frame answer may rest on evidence that does not speak about the exact time asked, provided its
reliability and scope justify the conclusion. There is no blanket rule in either direction. Weigh these
five things, in this order, and record them in `justification`:
1. **Standing (§8.1).**
   - `authoritative-record` and `direct-observation` can support a conclusion.
   - `reported` can, if corroborated or uncontradicted and from a source in a position to know.
   - `plan` supports only the plan, never that it happened.
   - `unverified` supports nothing on its own.
2. **Scope.** Does the evidence cover this entity, this kind of fact and this period?
   - A record that states it is complete for its scope (a current staff list "of all survey staff") is
     evidence about everyone it omits. Use the inference `closed-list`.
   - A record that does not state that it is complete is evidence only about what it contains.
3. **Timing.** How far is the time asked from the evidence? Consider:
   - whether the gap is bracketed by later evidence (a later source implying the state still held, or had
     not resumed)
   - whether the kind of state changes often (a meeting's chair) or rarely (an employer)
   - whether the documents would have been likely to record a change in that period
4. **Corroboration.** Independent sources pointing the same way strengthen the conclusion. Repeats and
   forwards do not (§8).
5. **Contrary evidence.** Any statement pointing the other way, even `unverified`, is listed as
   counter-evidence and weighed.
   - Contrary evidence of equal or higher standing gives `disputed`.
   - Weaker contrary evidence lowers your confidence.

**Outcomes:**
- **Justified:** a value with status `inferred` (inference `continuation`, `closed-list` or
  `combination`), with its justification and confidence.
- **Not justified:** `insufficient`, with the recorded state in `explanation`.
- **Borderline:** when two careful annotators could reasonably differ, keep both readings (§12.3). The main
  answer is the one you find better supported; the other is an alternative, with ambiguity `evidence`.

These rules are a judgement about evidence, not a calculation. The trial measures whether annotators apply
them consistently.

## 13. Evidence
### 13.1 Recording evidence
- Every `stated`, `inferred` or `disputed` answer lists its evidence as **sets**.
- Each set is a list of evidence items: segment id, the exact character span or spans, and the statement
  ids, if annotated.
- **A set is sufficient on its own.**
  - If an answer needs two sources together (one gives the role, another the date), both go in **one** set.
  - If two independent sources would each be enough, list **two** sets.
- Keep each set minimal: nothing in it can be removed without the answer losing its support. Every item in
  a set is therefore **essential**: the scoring gives full evidence credit only when all the essential items
  of at least one set are cited (scoring-protocol-v0.md §4.3).
- **Context:** material that helps but is not needed goes in a separate `context` list. Examples: the email
  showing a return came later, or a passage that confirms a name. It is never required for full credit.
- **Sets per frame:** an answer in the `actual` frame and one in the `recorded` frame may need different
  sets.
- For `disputed` answers, give a set for each side, and the value that side states with its surface forms
  (for example "complete" against "two boreholes outstanding"). Both sides together are the essential
  evidence.
- List **counter-evidence** too: material that points the other way, even if it does not overturn the
  answer.

### 13.2 Inference types
When the status is `inferred`, name each step:

| Inference | Meaning | Example |
|---|---|---|
| `continuation` | (recorded frame only) a state reported at one time is taken to persist in the records until a reported change. State the last time it was reported and that no later change is reported in the available documents. | "Joaquín stepped down on 10 March, and no return before 27 April is recorded, so the records show him not site lead on 1 April." |
| `combination` | two or more statements together give the answer | the minutes name the approver; an email gives the date it took effect |
| `date-calculation` | arithmetic on stated dates | "two weeks after 3 March" |
| `reference` | the answer depends on resolving a role reference or pronoun | "the site lead" on 5 March means Joaquín |
| `consequence` | an event implies a state | "appointed site lead on 2 January" gives site lead from 2 January |
| `closed-list` | a record that states it is complete for its scope omits the entity, so the state did not hold for it (§12.4) | a staff list "of all current survey staff, 1 October", issued by Tallis, does not include Ravi |
| `other` | describe it | |

**`continuation` is a default, not an observation.**
- **In the `recorded` frame** it always supports an answer: "the records show no change".
- **In the `actual` frame** it supports an answer only when the evidence's standing, scope and timing
  justify it (§12.4). Otherwise the answer is `insufficient`, with the recorded state in `explanation`.
- Always name the last recorded state, its time and standing, and the period with no recorded change.

### 13.3 Rejected candidates
Reasons:
- `rumour-only`
- `hedged-only`
- `corrected` (a later correction withdrew it)
- `retracted`
- `updated` (true earlier, not at the time asked)
- `plan-only`
- `outside-time-asked`
- `not-available-by-as-of`
- `wrong-reference`
- `other`

## 14. Disagreement, adjudication, confidence and unresolvable cases
### 14.1 Independent annotation
- Annotate alone. Record your time in `time-log.csv` as you go.
- When you finish, compute the SHA-256 of your files and send it to the implementer before looking at the
  other annotator's work (README.md, Procedure). This is the freeze.

### 14.2 Comparison and adjudication
- **Comparison:** the implementer lists every difference in `disagreements.csv`: missing or extra
  annotations, and field-by-field differences on matched ones.
- **Meeting:** both annotators meet and go through each difference. One `adjudication` record per
  difference gives the `outcome`:

| Outcome | Meaning |
|---|---|
| `a-correct` / `b-correct` | one reading follows the guidelines and the other does not |
| `both-acceptable` | the guidelines allow both; keep both as alternatives in the adjudicated gold |
| `merged` | the adjudicated annotation combines parts of both |
| `unresolvable` | the annotators still disagree after discussion, and the guidelines do not decide |

- Each record also gives the **cause** (guideline unclear, guideline silent, document ambiguous, annotator
  slip, genuine disagreement), and whether the guidelines should change.
- **Never edit the frozen files.** The adjudicated gold is a new file. The frozen files stay as they were, so
  that agreement can be measured honestly.

### 14.3 Confidence
Your confidence in your own annotation, not the source's certainty:

| Value | Meaning |
|---|---|
| `high` | a careful second reader would almost certainly agree |
| `medium` | this is the best reading, but another reasonable one exists; describe it in `note` |
| `low` | a guess; flag it for adjudication |

### 14.4 Genuinely unresolvable cases
- Some cases cannot be settled by the documents, or by discussion. Do not force them. Mark them
  `unresolvable`, keep both readings, and say which part of the documents or guidelines causes it.
- A question whose adjudicated answer is `unresolvable` is reported separately. It is not scored as if
  it had a single right answer; how it is scored is decided in the M1 protocol, not here.
- A high share of unresolvable cases is itself a trial finding about the documents or the guidelines, and is
  reported.

## 15. Annotation format
**Containers.**
- Files are JSON Lines: one JSON object per line, each with a `record` field naming its type.
- One file per document per annotator: `<document>.<annotator>.jsonl`.
- For the questions: `questions.jsonl`, plus `answers.<annotator>.jsonl` per annotator.
- One `adjudication.jsonl` after the meeting.
- **Spreadsheets:** annotators may instead fill in the spreadsheet template in `annotation-template/`.
  It converts to these files by fixed rules (its README). JSON Lines remains the canonical format.

**Fields.**
- Every record has `id` (unique within its file, prefixed by type: `seg-`, `ent-`, `men-`, `tim-`, `st-`,
  `ln-`, `jd-`, `q-`, `an-`), plus optional `note` and `confidence`.
- Offsets are character positions in the document's text file, counting from 0, with the end exclusive.
- Dates are ISO 8601.
- Lists hold plain values or small objects. Nothing is nested more than two levels deep, so every record
  type is also a table (§15.2).

### 15.1 Fields by record
```text
document     id, kind, title, file
segment      id, document, start, end, author (entity), author_role_text, written (time),
             available_from (time), relation: original | reply-to | quote-of | forward-of, related (segment)
entity       id, kind, name, aliases [text]
mention      id, segment, start, end, text, entity, reference: name | pronoun | role-reference | description,
             resolved: stated | inferred | unresolved
time         id, segment, start, end, text, value {from, to}, granularity,
             anchor: explicit | document-date | other-time | inferred | unresolvable, anchor_time (time)
statement    id, segment, spans [[start, end]], kind, description, predicate_text,
             participants [{role, entity | time | value | statement}],
             polarity: affirmed | negated, conveyed: stated | implied, commitment, modality,
             event_time (time), holds_from (time), holds_until (time), holds_at [time], due (time),
             asserted_by (entity), attribution, via [entity],
             standing: authoritative-record | direct-observation | reported | plan | unverified, standing_reason
link         id, type, from (statement), to (statement), marked: stated | inferred
judgement    id, about, kind, participants [...], times {event_time, holds_from, holds_until, holds_at},
             belief, based_on [statement], against [statement], reasoning, inference [type], explanation
question     id, text, answer_type, about_time {time or period, mode}, as_of (date),
             frame: recorded | actual | unspecified
answer       id, question, annotator, frame: recorded | actual, value {text, entity, forms [text]}, status,
             inference [type], explanation, evidence [[{segment, spans, statements}]],
             context [{segment, spans, statements}], counter_evidence [{segment, spans, statements}],
             alternatives [{value, status, inference, why}], ambiguity: none | wording | evidence | frame,
             justification, sides [{side, value, forms [text]}] (disputed answers),
             rejected_candidates [{value, reason}], annotator_view, question_problem
adjudication id, items [record ids from each annotator], field, outcome, cause, guideline_change, note
```

### 15.2 Why the format is neutral
- **Plain data:** the format is records of named fields with ids and references. It does not prescribe how
  a system stores or queries them.
  - **Python:** one class per record type; references are ids.
  - **A relational database such as PostgreSQL:** one table per record type, with list fields as child
    tables (for example `statement_participant(statement, role, kind, ref)` and
    `answer_evidence(answer, set_no, segment, start, end)`).
  - **A graph or knowledge-graph database such as TypeDB, or triples:** records become nodes, and
    references become edges or relationships.
  - **A text-only system:** the spans are its evidence.
- **Who decides a mapping:** a mapping for any system is written by that system's builders after the gold is
  frozen. It never changes the gold. Anything a system cannot express is counted against that system
  (README.md, coverage check), never removed from the gold.

## 16. Worked examples
These examples come from an invented world used only here: the **Brindle Harbour Authority** (the client),
**Oskarsen & Vey Engineering** (the contractor) and **Tallis Ground Survey Ltd** (a subcontractor),
working on the **North Quay sea-wall refurbishment**. The people are:
- Mirela Tanaka, the Authority's project director
- Joaquín Ferro, the contractor's site lead
- Hana Osei, the Authority's safety adviser
- Ravi Lindqvist, Tallis's survey manager
- Wen Abara, the contractor's commercial manager

All are fictional. The trial's own documents must use a different world, so that these examples cannot
leak answers.

The JSON below is abbreviated: offsets, ids of obvious records and some fields are left out.

**Frames in the examples.**
- Questions not marked with a frame are in the `actual` frame.
- Their answers rest on statements about the time asked, so the `recorded` frame would give the same
  answer.
- Examples 4 and 7 show questions where the two frames differ.

### Example 1: a multi-party decision with a condition (§4, §5)
> Minutes, 12 May 2026: "The project board, chaired by Mirela Tanaka, approved the revised drainage design
> on behalf of the Authority, provided Tallis completes the soil survey first."

```json
{"record":"statement","id":"st-1","kind":"decision","predicate_text":"approved",
 "description":"The project board approved the revised drainage design for the Authority, on condition that Tallis completes the soil survey first.",
 "participants":[{"role":"decider","entity":"ent-board"},{"role":"chair","entity":"ent-mirela"},
   {"role":"on-behalf-of","entity":"ent-authority"},{"role":"object","entity":"ent-drainage-design"},
   {"role":"condition","statement":"st-2"}],
 "polarity":"affirmed","conveyed":"stated","commitment":"certain","modality":"conditional",
 "event_time":"tim-12may","asserted_by":"ent-minutes-author","attribution":"direct"}
{"record":"statement","id":"st-2","kind":"obligation","predicate_text":"completes",
 "description":"Tallis is to complete the soil survey before the design approval applies.",
 "participants":[{"role":"obligated-party","entity":"ent-tallis"},{"role":"action","value":"complete the soil survey"}],
 "polarity":"affirmed","conveyed":"stated","commitment":"certain","modality":"required"}
{"record":"link","type":"depends-on","from":"st-1","to":"st-2","marked":"stated"}
```
- `chair` is not in the suggested role list. It is the annotator's own role name, which is allowed.
- The approval does not make the design approved *now*: it is `conditional`. Whether the condition was met
  is a separate question.

### Example 2: a moved deadline, a month without a year, and an update (§5, §7, §11)
> Email from Ravi Lindqvist, 14 April 2026: "The soil survey report is due in June."
> Email from Ravi Lindqvist, 2 June 2026: "Because of the borehole flooding, the report has been pushed back
> to the end of July."

- **"in June":** `{from: 2026-06-01, to: 2026-07-01}`, anchor `document-date`. The note says: future tense
  in an April email, so June 2026.
- **"the end of July":** `{from: 2026-07-25, to: 2026-08-01}`, anchor `document-date`, granularity
  `other`. The note says: "end of the month" taken as its last week.
- **The two obligations are linked** with `updates`, `marked: stated` ("pushed back"). The first was true
  when said, so this is not a correction.
- **The reason** ("borehole flooding") is a `reason` participant. Keep it, even if no question asks about
  it.

### Example 3: hearsay inside a forward (§7.4, §8)
> Email from Wen Abara to Mirela Tanaka, 9 May 2026: "FYI, see below."
> ---- Forwarded message ---- from Ravi Lindqvist, 2 May 2026: "Joaquín told me he's leaving the project at
> the end of the month."

```json
{"record":"segment","id":"seg-fwd","author":"ent-ravi","written":"tim-2may","available_from":"tim-9may",
 "relation":"forward-of","note":"available to Mirela from the forward on 9 May"}
{"record":"statement","id":"st-7","segment":"seg-fwd","kind":"event","predicate_text":"leaving",
 "description":"Joaquín plans to leave the project at the end of May.",
 "participants":[{"role":"actor","entity":"ent-joaquin"},{"role":"object","entity":"ent-project"}],
 "polarity":"affirmed","conveyed":"stated","commitment":"unknown","modality":"planned",
 "event_time":"tim-end-may","asserted_by":"ent-joaquin","attribution":"reported","via":["ent-ravi","ent-wen"]}
```
- **"The end of the month"** is anchored to Ravi's message date (May), not to the forward's.
- **Availability:**
  - For "as of 5 May, what did the Authority know?", this statement is not available: it reached Mirela on
    9 May.
  - For Ravi's own knowledge, it was available on 2 May.
- **Modality** is `planned`: nobody reports that Joaquín actually left.

### Example 4: negation, termination and reinstatement (§10)
> Minutes, 3 March 2026: "Hana Osei confirmed she is not the safety adviser for the quay works; that remains
> with the contractor."
> Minutes, 17 March 2026: "Joaquín Ferro stepped down as site lead on 10 March for family reasons."
> Email from Wen Abara, Monday 20 April 2026: "Good news: Joaquín is back as site lead from next Monday."

**Statements:**

| Id | What the source says | Recorded as |
|---|---|---|
| st-10 | Hana is not the safety adviser for the quay works | `state`, `polarity: negated`, `holds_at` 3 March. Nothing about other dates. No end date, and no implication that she ever was. |
| st-11 | the contractor holds that responsibility | `state`, affirmed, `holds_at` 3 March, `conveyed: stated` ("remains" also implies it held before; noted) |
| st-12 | Joaquín stepped down on 10 March | `event`, `event_time` 10 March, `reason` "family reasons" |
| st-13 | Joaquín was site lead until 10 March | `state`, `holds_until` 10 March, `conveyed: implied` by st-12 |
| st-14 | Joaquín is site lead again from Monday 27 April | `state`, `holds_from` 27 April (anchor `document-date`: "next Monday" after Monday 20 April), modality `planned` (it is announced before it starts), commitment `certain` |
| ln-1 | the reinstatement after the termination | `resumes`, from st-14 to st-13 |

**Questions:**
- **"According to the project records, was Joaquín site lead on 1 April 2026?"** (`recorded`)
  - Value: `no`.
  - Status: `inferred`, inference `continuation`. He is recorded as stepping down on 10 March, and no return
    before 27 April is recorded.
  - Evidence: one set, {st-12}.
  - Context: the 20 April email, which shows that the recorded return is later than 1 April.
- **"Was Joaquín actually site lead on 1 April 2026?"** (`actual`)
  - **Standings:**
    - st-12 is `reported`. The minutes record a departure announced to the meeting, and the documents do not
      show that the minutes are the contractor's record of appointments.
    - The 20 April email's implication that he is not site lead *now* is `direct-observation`: Wen, the
      contractor's commercial manager, is describing the contractor's own current staffing.
  - **Weighing (§12.4):**
    - two independent sources, consistent with each other
    - the period from 10 March to 20 April is bracketed: ended at the start, not yet resumed at the end
    - a site lead rarely changes twice in a month
    - no contrary evidence
  - **Main answer:** `no`, status `inferred` (inferences `continuation` and `combination`), confidence
    `medium`.
    - Evidence: one set, {st-12, the 20 April email}. Both items are essential.
    - Justification: "Departure reported on 10 March; the contractor's manager implies he was still not site
      lead on 20 April; nothing contrary in between."
  - **Alternative:** `insufficient`, ambiguity `evidence`.
    - Why it is defensible: the departure is second-hand, and a brief return in between would have gone
      unrecorded.
  - The gold keeps both. Under the revision 1 rule this question was `insufficient` by default. It is now
    weighed on the evidence.
- **"Was Joaquín site lead on 1 April 2026?"** (`unspecified`; ambiguity `frame`)
  - The gold holds both of the answers above.
  - Systems state which reading they answer. An answer that does not is scored against both readings, and
    the lower score counts (scoring-protocol-v0.md §4.2).
- **"Was Joaquín site lead on 4 May 2026?"** (`actual`)
  - Status: `insufficient`. Only a plan to return on 27 April is reported; nothing reports that he did.
  - Rejected candidate: `yes`, reason `plan-only`.
  - An annotator who thinks the return almost certainly happened writes that in `annotator_view`, and the
    status stays `insufficient`.
- **"Who was the safety adviser for the quay works on 3 March?"**
  - Value: the contractor (Oskarsen & Vey).
  - Status: `stated`, evidence {st-11}.
  - Rejected candidate: Hana Osei, reason `other` (explicitly negated, st-10).

### Example 5: a correction and an unresolved contradiction (§11, §12)
> Minutes, 10 February 2026: "Tallis started on site on 2 February."
> Email from Ravi Lindqvist, 12 February 2026: "Correction to the minutes: we started on 9 February, not
> 2 February."
> Status table "as of 30 June 2026", row Soil survey: "complete".
> Chat message from Joaquín Ferro, 30 June 2026: "survey still has two boreholes outstanding."

- **The start date:**
  - `ln-` `corrects`, from the email to the minutes, `marked: stated`.
  - "When did Tallis start on site?" is 9 February 2026, status `stated`, evidence {the email}.
  - Rejected candidate: 2 February, reason `corrected`.
  - As of 11 February the answer is 2 February, status `stated`: the correction was not yet available.
- **The survey:**
  - The table and the chat contradict each other on the same day, and neither refers to the other:
    `contradicts`, `marked: inferred`.
  - "Was the soil survey complete on 30 June?" is `disputed`, with an evidence set for each side.
  - The annotator must not decide by preferring the chat's detail or the table's formality. Any leaning goes
    in `annotator_view`.

### Example 6: an answer needing two sources, and an unknown (§12, §13)
> Minutes, 12 May 2026 (as in Example 1), and an email from Ravi Lindqvist, 20 May 2026: "Soil survey
> completed today; report to follow."

- **"Did the drainage-design approval have its condition met, and when?"**
  - Value: yes, on 20 May 2026.
  - Status: `inferred`, inference `combination`. The email states the completion, but no single source
    states that the approval's condition was met; that needs the minutes and the email together.
  - Evidence: **one** set containing both the minutes (the condition) and the email (the completion).
    Neither alone is sufficient.
- **"Who was the Authority's safety adviser for the harbour office building in March?"**
  - Nothing in the documents mentions that building's safety adviser. Status: `insufficient`.
  - The 3 March negation about the quay works is not evidence for a different site. If it is a tempting
    wrong answer, list it as a rejected candidate.
- **"As of 1 May 2026, was the soil survey complete?"**
  - No document available by 1 May mentions the survey's progress. Status: `not-yet-available`.
  - The later email exists but is not usable as of 1 May.

### Example 7: a termination with nothing recorded afterwards (§8.1, §10, §12.4)
> Email from Tallis Ground Survey Ltd's office, 1 July 2026: "Ravi Lindqvist left Tallis on 30 June. Please
> send survey queries to the office address."
>
> The documents end in July 2026. No later document mentions Ravi.

- **Standing:** `authoritative-record`.
  - `standing_reason`: Ravi's own employer is announcing his departure, and redirecting his work to its
    office.
  - The email's being "from the office" is not the reason. The employer's responsibility for its own staff
    is.
- **"According to the documents, was Ravi working for Tallis on 1 October 2026?"** (`recorded`)
  - Value: `no`.
  - Status: `inferred`, inference `continuation`.
  - Evidence: one set, {the 1 July email}.
  - Explanation: recorded as leaving on 30 June; no return is recorded.
- **"Was Ravi working for Tallis on 15 July 2026?"** (`actual`)
  - **Weighing (§12.4):**
    - authoritative standing
    - a gap of two weeks
    - an employer, which changes rarely
    - queries redirected away from him
    - no contrary evidence
  - **Main answer:** `no`, status `inferred` (inference `continuation`), confidence `high`.
  - Justification: "The employer announced his departure on 1 July; a return within two weeks is
    implausible, and nothing suggests one."
- **"Was Ravi actually working for Tallis on 1 October 2026?"** (`actual`)
  - **Weighing:** the standing is the same, but the gap is three months, and the documents end in July, so
    a return would not have been recorded in them.
  - **Main answer:** `insufficient`, with the recorded state in the explanation.
  - **Alternative:** `no`, status `inferred` (inference `continuation`), ambiguity `evidence`.
    - Why it is defensible: a departure announced by the employer usually lasts. A careful reader may accept
      three months.
  - The two questions differ only in timing. That is the point: the rule weighs evidence; it is not a
    blanket rule.

### Example 8: what makes a record authoritative (§8.1, §12.4)
> Email from Tallis's office, 2 October 2026: "Attached is our current register of all survey staff, as at
> 1 October." The register lists six names, not including Ravi Lindqvist.
> Attendance list in the minutes of 5 October 2026: eight names, not including Ravi Lindqvist.
> Chat message from Wen Abara, 6 October 2026: "someone said Ravi's back at Tallis?"

- **The register:** `authoritative-record`.
  - `standing_reason`: issued by the employer, and describing itself as complete ("all survey staff") and
    current ("as at 1 October").
  - "Was Ravi actually working for Tallis as survey staff on 1 October?": `no`, status `inferred`,
    inference `closed-list`, confidence `high`.
  - Evidence: {the register email}. The 1 July email is context.
  - The scope matters. The register is evidence only about **survey** staff. It says nothing about whether
    Ravi held some other role at Tallis.
- **The attendance list:** `direct-observation`, of who attended. It does not state that it is a list of
  Tallis staff, or that it is complete for any such scope.
  - Ravi's absence from it is not evidence about his employment.
  - It is a list, and it appears in the minutes, but neither of those makes it authoritative.
- **The chat:** `unverified` ("someone said", with a question mark).
  - It is listed as counter-evidence. It does not create a dispute, because it is much weaker than the
    register.
  - It does not lower the confidence below `high` for 1 October: written on 6 October, it hints at a return
    after the register's date, not on it. An annotator who reads it otherwise records `medium` and a note.

## 17. For the primary author: writing documents and questions
These guidelines are for annotation, but the trial's author also writes the documents. To keep them
realistic and fair to every kind of system:
- **Write as the people in the world would.** Include:
  - chatter, digressions, pronouns and role references
  - facts implied but never stated
  - tables with numbers and status words
  - typos in chat
  - quoted replies and forwards
- **Put facts only where the people would put them.** Do not write sentences shaped for annotation ("X
  held role Y from date A to date B").
- **Include detail no question needs:** reasons, opinions, caveats.
- **Write questions as a project member would ask them.** Include:
  - Some that only need one passage found and read: plain retrieval questions, at least one in six.
  - At least one whose answer is a reason, caveat or opinion in the source's own words (`short-text`).
- **Include material that is awkward to structure** (bias audit B3, B9):
  - numbers in tables
  - long conditions quoted verbatim
  - a fact that is only implied
  - a statement whose meaning depends on tone or context
- **Ask nothing because it is easy to structure,** and leave nothing out because it is hard to.
- Write the answers from the world script and the documents, before anyone runs a system.

## 18. Changes expected after the trial
These are recorded in the trial report, not decided now:
- whether `implied` and `inferred` can be told apart consistently
- whether the suggested role names are enough
- the range conventions for vague time words
- whether `continuation` answers should have their own status
- whether annotators weigh standing, scope and timing consistently for actual-frame answers (§12.4,
  Examples 4, 7 and 8)
- whether the five standings (§8.1) can be told apart consistently, especially `authoritative-record`
- whether authors and annotators classify question frames consistently
- whether alternatives are added consistently, or too freely
- how `unresolvable` questions are scored in M1
