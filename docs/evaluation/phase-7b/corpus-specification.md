# Corpus specification

There are two sets, scored separately and never combined into one headline figure. Neither exists yet:
both must be written by people other than the developer (see the README, under status).

## S1: specialist evidence passages (primary), about 40 passages
**What a passage is:** short documents of the kind an analyst's memory would ingest, 40–250 words each:
- emails and forwarded emails
- meeting minutes
- press releases and news excerpts
- internal notes, letters and filings summaries
- chat messages between colleagues

**Fictional entities only:**
- **Organisations and people:** invented.
- **Places and dates:** may be real.
- **No real organisation or person** may be described as doing something.

**Coverage targets** (a passage can count towards several; minimum passages per row):

| Phenomenon | Min | Notes |
|---|---|---|
| appointments, joining, promotion | 5 | named roles and titles; first person and third person |
| departures, dismissals, resignations | 4 | include euphemisms ("stepped down", "parted ways") |
| reporting and authority lines | 4 | including "manages", possessives, interim arrangements |
| corporate ownership and control | 4 | subsidiaries, acquisitions, stakes, board control (out of the typed domain) |
| investigations and disputed allegations | 4 | "is alleged to", "denies", "under investigation" |
| several sources on one event | 4 | at least 2 sets of 2–3 passages about the same event, with disagreement |
| forwarded versus independent | 4 | the same claim forwarded, versus independently observed |
| corrections and retractions | 4 | explicit ("Correction:") and implicit ("I misspoke …") |
| change over time | 4 | the same relation at different times, in one or several passages |
| ambiguous identity | 3 | two people with the same name; initials; a role without a name |
| uncertain dates | 4 | "around 2019", "early last year", "since spring", a missing year |
| plans, conditional and hypothetical | 4 | "will join if approved", "would have left" |
| negative controls (no admissible assertion) | 5 | questions, opinions, scheduling, pure speculation, boilerplate |

**Format** (annotation-templates/passages.csv):
- **Fields:** a passage id, set `S1`, an author id (the contributor's code, not their name), a document kind,
  the stated author or sender within the fiction, the document date (or "unknown"), an optional thread id
  (for passages to be read in order), and the text.
- **Threads:** passages in one thread are ingested in order. Corrections may target earlier passages in the
  thread.

**Size and power:**
- **What 40 passages give:** about 80–150 gold assertions.
- **What that can detect:** proportions with 95% intervals of about ±8–11 points, enough to detect a recall
  difference of about 20 points, not small differences (success-criteria.md).

## S2: conversational turns (secondary), about 40 turns in 10–15 short threads
**Source:**
- **Preferred:** written by contributors, as dialogues between two or three fictional people.
- **Alternative:** development-split turns from LoCoMo and LongMemEval, drawn by a new seeded rule that excludes
  every Phase 7A sampled turn.
  - **Its weaknesses:** it is not independently authored and carries the datasets' licences.
  - **How it is labelled:** "benchmark development turns".
  - **What is never used:** held-out turns and questions.

**Coverage targets:**

| Phenomenon | Min |
|---|---|
| pronouns and coreference across turns | 5 |
| first-person assertions (job, home, relationships) | 6 |
| informal phrasing, ellipsis, slang | 5 |
| implicit relationships ("my boss", "our team") | 4 |
| preferences and decisions | 4 |
| corrections ("actually, it was June") | 3 |
| relative time ("last spring", "two weeks ago") | 4 |
| contradictions between turns or speakers | 3 |
| filler, greetings, questions (negative controls) | 6 |

**Format:** as for S1, set `S2`. `thread_id` and `turn` order are required, and each turn's speaker is
required.

## Development material (never scored as evidence)
- **What it is:** a separate set of about 10 developer-authored passages and turns, labelled `DEV`.
- **What it is for:** prompt and validator development only.
- **What also counts as development:** everything in Phases 6B, 6C and 7A (frozen sets, adversarial cases,
  probes).
- **What it may not be:** none of it may be counted in S1 or S2 figures.

## Independence and provenance rules
1. **Authors:** S1 and S2 authors are not the developer, and do not see the extractor, its prompt or its
   outputs before freezing.
2. **Authors' instructions:** they get only this specification and the domain description. They do not get
   `rules:v2.1`'s patterns or the model prompt.
3. **Annotators:** at least two, neither the developer, and at least one not an author of the passages
   they annotate.
4. **Adjudication:** by a third person, or by the two annotators jointly with a recorded rationale (see
   annotation-guidelines.md).
5. **Claude Code generates neither passages nor gold.** If no independent contributors are available, the
   experiment stops at this stage.
6. **Contributor declaration:** every contributor signs `annotation-templates/contributor-declaration.md`
   (role, no exposure to outputs, no generative-AI help in writing the passages or gold).
