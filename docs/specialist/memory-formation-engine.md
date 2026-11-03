# Memory Formation Engine: proposed architecture

Status: **proposal for review, not implemented.** Builds on ADRs 0001-0008; changes to them are listed
explicitly at the end.

## Goal
Turn complex source material (meeting notes, emails, reports, chat) into reliable structured memory:
entities, events, claims and n-ary relationships with explicit roles, each tied to its evidence, with its
temporal validity and uncertainty, compared with what is already known, and never accepted as true just
because it was extracted.

## Three separate decisions
Every candidate passes three questions, recorded separately, by different components, with reasons:

| Decision | Question | Who decides | Recorded as | Effect |
|---|---|---|---|---|
| **Salience** | Is this worth keeping as structured memory? | salience assessor (rules or model) | `salience-assessment` on the segment or candidate | Low salience: source text kept, nothing structured. Never deletes source. |
| **Support** | Does the source actually say this? | support assessor (span check + entailment provider) | `support-assessment`: explicit / paraphrased / inferred / unsupported, with the span | Unsupported candidates are kept as rejected candidates for audit, never become claims. |
| **Acceptance** | Should this be believed as current knowledge? | acceptance policy + human review (existing `review`) | `review` (existing) | Only accepted claims are "believed" (ADR 0003). |

A claim can be salient and well supported and still not accepted (a supported quote of a wrong report);
a claim can be accepted while old (history). The three are never merged into one score.

## Pipeline

```
source document ──► 0 intake ──► 1 segment ──► 2 salience ──► 3 extract candidates ──► 4 support check
                                                                                          │
              8 acceptance policy ◄── 7 schema-gap proposals ◄── 6 change analysis ◄── 5 resolve + time
```

0. **Intake and retention.** Store the whole source document verbatim with source, author/authority,
   document date and content hash (`source-document`, new). Segments and claims point back to
   character offsets. Re-processing with a better extractor reuses the stored document (ADR 0004 ids).
1. **Segmentation.** Deterministic: paragraphs, messages, list items, table rows; each a `segment`
   (today's `observation`) with offsets into the document.
2. **Salience.** Per segment: keep for structure, keep as text only, or ignore for structure (greetings,
   boilerplate). Recorded with method and reason. Text is always retained.
3. **Candidate extraction** through a provider interface (as `Extractor` today), returning:
   - mentions and candidate entities (people, organisations, teams, projects, deliverables);
   - events (decided, approved, assigned, moved deadline, reported status) with participants by role;
   - n-ary relations with explicit roles (e.g. `approval(approver, item, condition, on-behalf-of)`);
   - claim modality: asserted, reported ("X said that ..."), planned/expected, hypothetical, negated, asked;
   - attribution: who asserts it (the document author, or a person quoted in it);
   - quoted time phrases (never dates; ADR 0005) and explicit/inferred basis.
   Providers: deterministic fixture, rule-based, **simulated LLM** (canned structured outputs keyed by
   segment hash, labelled `simulated` everywhere) and later a real LLM. Results from simulated providers
   are never reported as extraction performance.
4. **Support check.** Exact span alignment (exists today), then an entailment provider (simulated or real)
   decides explicit / paraphrased / inferred / unsupported. Reported speech is supported as "X reported
   Y", not as Y.
5. **Resolution and time.** Entity resolution proposes links (identity claims, never merges; ADR 0006).
   Time phrases are normalised deterministically into windows (`gupi.timeexpr`); event time, report time
   and validity are kept apart.
6. **Change analysis** against existing memory, using TypeDB queries over the same proposition, the same
   players and domain constraints (ADR 0006/0007): *new*, *corroborates*, *refines* (narrower bounds),
   *updates* (later state of a changing fact), *contradicts*, *retracts/corrects*. Each becomes a
   `change-candidate` for review, e.g. a proposed supersession; nothing is applied automatically.
7. **Schema-gap proposals.** When candidates do not fit existing types or roles (today: rejected), record a
   `schema-proposal` (suggested type, roles, example spans, count). Humans decide; the schema changes only
   through a reviewed migration (ADR 0004). No automatic schema evolution.
8. **Acceptance policy.** Configurable rules propose a review outcome (e.g. "single unsupported report:
   leave as hypothesis"; "contradicts an accepted claim: needs review"; "corroborated by two authoritative
   sources: suggest accept"). Default: everything goes to human review. Automatic acceptance only for
   sources explicitly configured as authoritative, and still recorded as a review by the policy.

## Proposed schema additions (core/0010, not written yet)
`source-document` (verbatim text, hash, document date, authority), `segment` (subtype or role of
observation with offsets), `formation-run` (provider, versions, budget), `salience-assessment`,
`support-assessment` (level, span, method), `attribution` (who asserts a claim; distinct from authorship of
the text), claim `modality`, `change-candidate` (kind, target claims), `schema-proposal`.

## What stays the same
TypeDB as the only store; ids from content; values as query parameters; reviews and supersessions as
historical events; spell assembly and same-spell rules; offline by default; budgets for any real LLM.

## Open questions for review
- Should segments be observations (reuse) or a new type with observations as their parents? (Proposal:
  keep `observation` as the segment; add `source-document` as its parent.)
- How much of the support decision can be deterministic without an entailment model? (Proposal: exact and
  near-exact span support deterministic; paraphrase and inference only with a provider, otherwise
  "unverified".)
- Acceptance policy defaults per source type (minutes vs chat vs official announcements).
