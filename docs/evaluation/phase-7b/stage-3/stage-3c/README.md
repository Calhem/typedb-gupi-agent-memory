# Phase 7B Stage 3C: adjudication preparation and failure diagnosis

**Status (2026-11-04):** diagnosis complete; **independent adjudication not yet done.**
- **Branch:** `feature/phase-7b-stage-3c-adjudication`, from Stage 3B (`e273a72`). Not merged.
- **No production change:** extraction, format 1.1, formation, persistence and schema are all unchanged.
- **Nothing rerun:** no extraction was rerun, no model was called, and $0 was spent.

**Why there are no revised metrics:** no human reviewer independent of GUPI and of the gold was available. The
gold's author (Claude) must not adjudicate its own disputed answers, and a model-assisted second opinion needs the
owner's approval first. So this stage gives the **original Stage 3B figures unchanged**, plus **bounds** on what
adjudication could change. It issues no revised score.

## Files
| File | What it holds |
|---|---|
| [adjudication-protocol.md](adjudication-protocol.md) | the review package, who may adjudicate, and how decisions become a new gold version |
| [severe-error-analysis.md](severe-error-analysis.md) | the five severe errors, one by one |
| [failure-attribution.md](failure-attribution.md) | failure modes A–F: what failed, and where (model, format, validator, formation, scoring) |
| [formation-safeguards.md](formation-safeguards.md) | the 30 formation decisions reconstructed; which safeguards worked and which did not |
| [proposed-remediation.md](proposed-remediation.md) | design proposals only, ranked by correctness impact |
| [remaining-limitations.md](remaining-limitations.md) | what this stage cannot settle |

**Private, outside the repository** (`gupi-stage3-private/stage3c/`):
- the adjudication package (19 items, blank decisions sheet)
- the reconstructed formation decisions
- the severe-error record with gold interpretations

## Original Stage 3B results, preserved unadjudicated
| Metric | Result |
|---|---|
| precision | 21/30 |
| recall | 21/39 (baseline `rules:v2.1`: 3/39, frozen) |
| F1 | 0.61 |
| partial / overlapping-unmatched / unsupported | 7 / 1 / 1 |
| severe errors (formed) | 5 (3) |
| exact matches formed; review; withheld | 15; 4; 9 |
| frozen transcript audit | invalid: desktop transcript artefacts. The tool-call inspection is supporting evidence, not a pass |

## Bounds (not a revised score)
These assume the adjudicator decides only the listed items, and changes nothing else.

| Quantity | Original | Possible range after adjudication |
|---|---|---|
| precision | 21/30 | 21/30 to 29/30; 29/29 if the unsupported question is ruled a gold omission |
| recall | 21/39 | 21/39 to 29/39 on the same gold; up to 29/36 if the three disputed gold assertions (items 11–12) are ruled gold errors |
| formed severe errors | 3 | 0 to 3 |

## Correction to the Stage 3B report
Stage 3B described the twelve disputed items as "7 partial, 1 overlapping, 4 disputed misses". In fact:
- **3 are misses** (X3-07, X3-29, X3-30).
- **The fourth (X3-09, item 9) is a matched candidate** that carries a severe-error label (invented claimant).

The package lists it as such.

## What the diagnosis found
These findings are established from the code, the frozen documents and the source text, not from the gold:
1. **Statements lose structure.** A statement's object participant is not tied to its object text.
   - **The result:** the structured roles of a formed statement can say something the source does not.
     - "LANTERN-7 is operated by COPPER MOTH", from "operated by the same team as".
     - "Morrow & Fane has opened Dmitri Sava", with "an internal investigation" carried only as separate text.
   - **Why validation can't catch it:** format 1.1 and the validators check structure and grounding, not whether
     the roles reproduce the proposition.
2. **A bare retraction is silently lost.** "Sorry, ignore what I said yesterday about Gareth" produces no
   candidate, so the retracted claim stays formed, with no flag for review.
   - **Why:** format 1.1 attaches a correction only to an assertion.
3. **"Former" cannot be expressed.** The X3-09 employment was formed with no time.
   - **What is safe:** GUPI answers UNKNOWN, not TRUE, for whether it holds now.
   - **What is lost:** the source's evidence that it has ended (by the document date), and the "former" in the
     stored title.
4. **The model's abstentions on identity follow the frozen format rules.** The format says to mark "a name you
   cannot tie to one individual" as vague.
   - **The surname cases** ("Hale") are the closer calls.
   - **The two-Daniel-Reyes case:** under GUPI's known limitation S8, extracting both would have merged two people
     into one referent.
5. **Claimant kind `unknown` for named people follows the frozen rule.** The rule says to use `person` "only when
   the passage establishes it", and those passages give only the name.
6. **A cue-less contradiction cannot be marked in format 1.1,** because a correction needs a cue. GUPI's
   answering layer already reports the two disagreeing start dates as disputed.
7. **The safeguards worked where they apply.**
   - **Withheld by modality:** the question, the plan and the condition.
   - **Sent to review:** hedges and stated corrections.
   - **Withheld as a copy:** the forwarded copy.
   - **Withheld because the time is only a day:** day-window events.
   - **Never formed:** inferred and vague references.
   - **What they don't check:** none of these safeguards checks semantic faithfulness.

## The decision this stage prepares
**Does GUPI need targeted evidence-integrity fixes before automated model integration?**
- **The diagnosis says yes, for two essential items:**
  - statement role faithfulness (finding 1)
  - bare retractions (finding 2)
- **Neither depends on how the disputed items are adjudicated.**
- **See** proposed-remediation.md. Nothing is implemented.
