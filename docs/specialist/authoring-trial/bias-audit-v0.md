# Bias audit of the annotation guidelines, draft v0

Date: 2026-11-03. Status: **revision 2, provisional**, together with guidelines-v0.md (revision 2),
scoring-protocol-v0.md (primary) and scoring-nl-experimental-v0.md (experimental). Revision 1 updated B8 and
added B14-B16. Revision 2 updates B7, B8 and B14-B16 for the answer contract and evidence standing, and adds B17-B21.

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
| **B7** | §12, scoring-protocol §2 | **Status labels.** Answers carry a status (`stated`, `inferred`, `disputed`, `insufficient`, `not-yet-available`). Systems with explicit uncertainty states produce these directly; a text reader must choose one. | **Revised:** every system fills the same contract field from the same plain-language definitions (scoring-protocol Appendix A). No natural-language parsing is used in the primary score. | See B17 on how close the labels are to GUPI's own. |
| **B8** | §8.1, §12.1, §12.4, §13.2, Examples 4, 7 and 8 | **Continuation as a default.** "A reported end persists until a reported return" is easy for a system that stores state changes, and harder for one that must reason over passages. | **Revised twice:** questions state a frame. In the actual frame, continuation is accepted only when the evidence's standing, scope and timing justify it, with a written justification. Borderline cases keep alternatives, which earn full credit. | Weighing standing is a judgement. Measure annotator agreement on it in the trial. Report results by frame (scoring-protocol §4.6). |
| **B9** | §5, §13.1 | **Phenomenon mix.** The trial's phenomena (n-ary approvals, multi-source answers, termination and reinstatement) are where structured systems are expected to be strong. | Plain retrieval questions are at least one in six. **Applied:** §17 asks for numbers in tables, verbatim conditions and context-dependent statements. | M1 quotas apply (at least 20% retrieval). Note that the two-document trial is too small to balance the mix, which is acceptable because it is not scored. |
| **B10** | §3 | **Resolved entities.** The gold resolves names, pronouns and role references to entities. Diagnostic "gold-statement" runs that feed this to structured systems give them resolution for free. | Gold is never ingested in normal runs. | M1 labels gold-statement runs as upper-bound diagnostics (m1-protocol.md §7); they are never compared with text systems. |
| **B11** | §15 | **Graph-shaped format.** Records with ids and references may look easier to load into a graph database than into tables. | The nesting depth is two levels, so every record type is a table, with list fields as child tables. §15.2 sketches Python, relational, graph and text uses equally. | Low. Revisit if a mapping proves awkward in practice. |
| **B12** | §10 | **Negation as polarity.** Recording negations as negated statements resembles a polarity attribute. | A text system keeps the negation in the passage itself, so this is unlikely to tilt answers. The rule "a negation covers only what it states" applies equally to every reader. | Low. |
| **B13** | §7.4, §12 | **"As of" questions.** Questions limited to what was available by a date suit systems that record when information arrived. | Any system can filter documents by their dates. The format records `available_from` per segment, not per fact. | Keep as-of questions to realistic ones ("what did the Authority know on 5 May?"). |
| **B14** | scoring-nl-experimental §3, Appendix A | **Templated output.** Fixed word lists and the first-sentence rule are read more reliably from systems that emit templated sentences. | **Revised:** these now apply only to the experimental secondary metric. The primary score uses the contract. | If the experimental metric is reported, report its scorer error rate per system. |
| **B15** | scoring-protocol §2, §4.3 | **Citing by segment id** suits systems that keep segment ids with what they store. | **Revised:** the corpus every system receives shows each segment's id in the text itself, so a text reader sees the ids it must cite. | Check in the trial that a text-only system can cite by id without loss. |
| **B16** | scoring-nl-experimental §5.2 caps | **Qualification rewarded on ambiguous questions.** Requiring a hedge or "according to the records" for full credit suits systems built to emit qualifiers. | **Revised:** the primary score has no such caps. The declared uncertainty and frame replace them, and alternatives earn full credit. The caps remain only in the experimental metric. | Low for the primary score. |
| **B17** | scoring-protocol §2, Appendix A | **Labels close to GUPI's.** The contract's uncertainty labels are the gold's statuses, which resemble GUPI's answer kinds (B1). A system built by the same author may map onto them more naturally. | Identical definitions for all systems. `stated` and `inferred` earn equal credit, so the finest distinction carries no score. | Each system's mapping from its own outputs to the labels is written down and frozen before any held-out run, and checked by the independent reviewer. |
| **B18** | scoring-protocol §3 | **Structured output required.** Systems that already produce structured records find the JSON contract easier. Text readers must format their output, and may fail validation. | Contract failures are reported separately, not as wrong answers. The instructions are the same for all. | If a system needs a formatting wrapper, the wrapper is fixed in advance, applied identically, and may only reformat, never add reasoning. Report contract-failure rates per system. |
| **B19** | guidelines §8.1, §12.4 | **Evidence standing.** Questions whose answers hinge on authority and scope may suit systems that store source metadata. | Standing is in the gold only; systems are scored on answers and evidence. Text readers see the same documents, which state the responsibilities and scopes. | In the trial, count how many questions depend on standing, and keep them in proportion. |
| **B20** | scoring-protocol §6 | **Audit by people.** Auditors may favour fluent or templated explanations. | Blind to system identity, with answers shuffled across systems. The form asks about content only (consistency with the documents, support), not style. | Report per-item auditor agreement. Consider normalising explanations' formatting before the audit. |
| **B21** | scoring-protocol §4.1 | **Exact value matching** favours systems that return canonical names, as structured systems tend to. | The gold lists generous forms (aliases, abbreviations, date formats). The audit logs answers judged correct but unmatched. | Report unmatched-but-correct answers per system. If they differ materially, widen the gold forms by a recorded amendment before any held-out run. |

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
3. Revision 1: continuation is limited to the recorded frame (B8).
4. Revision 1: quoted passages count as citations equally with segment ids (B15). Superseded in revision 2:
   segment ids are shown in the text of the corpus.
5. Revision 2: the primary score uses a common structured contract; word lists and the first-sentence rule
   are confined to the experimental metric (B7, B14, B16).
6. Revision 2: actual-frame answers are weighed by standing, scope and timing, not by a blanket rule (B8).

## Items for the owner
1. **An independent reviewer** of the guidelines before they are frozen (B1). This is now approved, using
   review-checklist-v0.md.
2. **Actual-frame answers:** weighed by evidence standing in revision 2 (B8, B19). Still open: whether
   annotators can apply the weighing consistently, which the trial measures.
3. **Scoring:** the primary protocol is scoring-protocol-v0.md (B7, B17). Still to be reviewed, frozen, and
   later written into the M1 protocol.
4. **Trial measurements to add to the report:**
   - implied statements, facts that appear only in tables, and pronoun and role references (B6)
   - free-text answers (B3)
   - use of `other` and of annotators' own role names (B4)
   - questions depending on evidence standing (B19)
5. **Per-system rates** in the trial report:
   - contract failures (B18)
   - unmatched-but-correct values (B21)
   - auditor agreement (B20)
6. **System mappings** onto the contract's labels, frozen and reviewed before any held-out run (B17).
