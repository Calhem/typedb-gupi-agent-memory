# Bias audit of the annotation guidelines, draft v0

Date: 2026-11-03. Status: **for the owner's review**, together with guidelines-v0.md.

## Question asked
Where might the guidelines favour systems that build structured knowledge representations? These include
GUPI, and the reified-triple and relational baselines. The comparison is with systems that retrieve and
read text.

## Method
- Each section of guidelines-v0.md was read against four questions:
  - Does the section shape the documents?
  - Does it shape the questions?
  - Does it shape the gold?
  - Does it shape how systems are compared?
- Each finding gives:
  - where it arises
  - how it could tilt results
  - what v0 already does about it
  - what remains for the owner or the M1 protocol
- Mitigations marked **applied** were made to the guidelines as a result of this audit.

**Limitation of the audit itself.** It was carried out by the same author who drafted the guidelines and
designed GUPI. A self-audit can find tilts, but cannot certify their absence. Finding B1 makes this explicit.

## Findings
| # | Where | Risk | Mitigation in v0 | Remaining |
|---|---|---|---|---|
| **B1** | the whole document | **Author familiarity.** The guidelines were drafted by GUPI's designer. Several categories closely resemble GUPI's model (listed below), which could make the gold easy to map onto GUPI and harder for others. | Each such category is grounded in earlier, public annotation practice: TimeML-style time ranges and granularity, FactBank-style source and certainty, FEVER/AVeriTeC-style verdicts, ACE/ERE-style event arguments. The categories were defined from the documents' domain without consulting GUPI's schema or ADR 0009. | **High.** It needs an independent reviewer before the guidelines are frozen (recommended), plus the owner's review. The trial's disagreement and limitation logs give independent evidence. |
| **B2** | §2, §15 | **Record-matching evaluation.** Gold written as statement records invites scoring systems on reproducing those records, which only structured systems can do. | **Applied:** §2 now says systems are compared only on answers and evidence; the source layer is for annotator agreement and diagnostics. | The M1 scoring rules must keep to this. Statement-level extraction scores, if reported, are labelled as a diagnostic of structured systems only. |
| **B3** | §4 | **Lost unstructurable detail.** Participants and roles make it natural to drop reasons, nuance and caveats, and then to ask only about what was kept. | §4 tells annotators to keep such detail in `description` and `note`. **Applied:** §17 asks for at least one question answered by a reason or caveat in the source's words, and for awkward material. | Check in the trial: the share of questions whose answers are free text. |
| **B4** | §4, §11, §13 | **Lists that read as a schema.** Role names, link types and inference types can steer annotators towards relation-shaped readings. | Roles are suggestions, and annotators may add their own (Example 1 does). The other lists include `other`. | Record in the trial how often `other` or own role names are used. A high rate means the lists are too narrow; a zero rate may mean they are steering. |
| **B5** | §7 | **Time normalisation.** Turning time phrases into date ranges suits systems with interval arithmetic. | The gold keeps the verbatim phrase and its anchor. Questions are asked in natural language; normalised ranges are not given to any system. | M1 quotas keep time-heavy question families in proportion (m1-protocol.md §5). |
| **B6** | §17 | **Annotation-friendly writing.** An author who knows the guidelines may write crisp, extractable sentences ("X held role Y from A to B"), which favours rule and structured extraction. | §17 asks for natural writing: implied facts, pronouns, tables, chatter, typos and forwards. It forbids annotation-shaped sentences. | Measure in the trial: the share of statements that are `implied`, the share of facts that appear only in tables, and the share of mentions that are pronouns or role references. |
| **B7** | §12 | **Status labels.** Answers carry a status (`stated`, `inferred`, `disputed`, `insufficient`, `not-yet-available`). Systems with explicit uncertainty states produce these directly; a text reader must say them in words. | The statuses describe the documents, not any system's output. | **For M1:** a fixed rubric that maps any system's natural-language answer onto the statuses, applied the same way to all systems. Retrieval-only systems continue to be scored on evidence sufficiency. |
| **B8** | §13.2, Example 4 | **Continuation as a default.** "A reported end persists until a reported return" is easy for a system that stores state changes, and harder for one that must reason over passages. It is also a default, not a fact. | It is always labelled `inferred` (`continuation`), never `stated`, and may be scored separately. | **Owner decision for M1:** whether `insufficient` is also accepted for continuation questions. A careful human might answer either way. |
| **B9** | §5, §13.1 | **Phenomenon mix.** The trial's phenomena (n-ary approvals, multi-source answers, termination and reinstatement) are where structured systems are expected to be strong. | Plain retrieval questions are at least one in six. **Applied:** §17 asks for numbers in tables, verbatim conditions and context-dependent statements. | M1 quotas apply (at least 20% retrieval). Note that the two-document trial is too small to balance the mix, which is acceptable because it is not scored. |
| **B10** | §3 | **Resolved entities.** The gold resolves names, pronouns and role references to entities. Diagnostic "gold-statement" runs that feed this to structured systems give them resolution for free. | Gold is never ingested in normal runs. | M1 labels gold-statement runs as upper-bound diagnostics (m1-protocol.md §7); they are never compared with text systems. |
| **B11** | §15 | **Graph-shaped format.** Records with ids and references may look easier to load into a graph database than into tables. | The nesting depth is two levels, so every record type is a table, with list fields as child tables. §15.2 sketches Python, relational, graph and text uses equally. | Low. Revisit if a mapping proves awkward in practice. |
| **B12** | §10 | **Negation as polarity.** Recording negations as negated statements resembles a polarity attribute. | A text system keeps the negation in the passage itself, so this is unlikely to tilt answers. The rule "a negation covers only what it states" applies equally to every reader. | Low. |
| **B13** | §7.4, §12 | **"As of" questions.** Questions limited to what was available by a date suit systems that record when information arrived. | Any system can filter documents by their dates. The format records `available_from` per segment, not per fact. | Keep as-of questions to realistic ones ("what did the Authority know on 5 May?"). |

### Resemblances to GUPI found under B1
These are disclosed so that a reviewer can judge them.

| Guidelines | Resembles | Difference |
|---|---|---|
| Time values as ranges [from, to) | GUPI's boundary windows | TimeML-style; the guidelines keep the verbatim phrase and its anchor, which GUPI does not |
| Answer statuses | GUPI's answer kinds | not one to one: `inferred` covers both continuation and combination, which GUPI v1 and the v2 proposal treat differently; `stated` vs `inferred` cuts across TRUE and FALSE |
| `continuation` inference | the v2 proposal's `termination-continuing` | here it is any state persisting, positive or negative, always labelled as an annotator's inference |
| `as_of` | GUPI's belief time | defined by document availability only; no review or acceptance step |
| Negated statements | the proposed polarity attribute (ADR 0009 Q4) | standard in factuality annotation (FactBank) |
| Participants with roles | typed n-ary relations | ACE/ERE-style event arguments; roles are open |

The differences in the answer statuses mean that mapping the gold onto GUPI will be lossy in both
directions. That is the intended outcome of an independent gold, and the coverage check will record it.

## Mitigations applied to the guidelines
1. §2: systems are compared on answers and evidence only (B2).
2. §17: a free-text-answer question, awkward material, and "ask nothing because it is easy to structure"
   (B3, B9).

## Items for the owner
1. **An independent reviewer** of the guidelines before they are frozen (B1). This is recommended, and is the
   only strong remedy for author familiarity.
2. **Continuation questions:** whether `insufficient` is also an acceptable answer in M1 scoring (B8).
3. **A status rubric** for scoring natural-language answers, to be written into the M1 protocol (B7).
4. **Trial measurements to add to the report:**
   - implied statements, facts that appear only in tables, and pronoun and role references (B6)
   - free-text answers (B3)
   - use of `other` and of annotators' own role names (B4)
