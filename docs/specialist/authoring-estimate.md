# Held-out authoring: effort estimate

Date: 2026-11-03. Estimates for an author who knows the domain but not GUPI's code, working from frozen
guidelines (m1-protocol.md §6). Ranges reflect writing speed and how much revision the gold needs. They
exclude the implementer's time and are estimates, not measurements.

**Order (approved 2026-11-03):** a two-document authoring trial first (authoring-trial/README.md), then the
eight-document mini-pilot, then the full split. Each stage's measured times replace the estimates for the
next.

## Two-document authoring trial (first)
| Task | Hours |
|---|---|
| Read the draft guidelines (both people) | 1-2 each |
| Small world script (6-8 people, 10-15 events) | 1-1.5 |
| 2 documents (about 400 words each) | 1-1.5 |
| Gold for 2 documents | 1-1.5 |
| 6 questions with gold answers | 0.5-1 |
| **Primary author total** | **4.5-7.5 h** (about 1 day) |
| Second annotator: 2 documents and 6 answers | 1.5-2.5 |
| Adjudication (both people) | 1-1.5 each |
| Implementer: comparison, coverage check, trial report | not counted |

Writing the draft guidelines comes before the trial and is not included.

## Full held-out split: 24 documents, 48 questions
| Task | Unit effort | Quantity | Hours |
|---|---|---|---|
| Read the guidelines and examples | — | once | 2-3 |
| World script: 3 organisations, 25-40 people, dated timeline of roles, decisions, deadlines, dependencies, reports, corrections, rumours | — | once | 4-6 |
| Documents (mixed kinds; average about 300 words; minutes and email threads longer, chat shorter) | 25-40 min | 24 | 10-16 |
| Gold per document: claims with roles, values, modality, assertor, time phrases (explicit or inferred), support level, salience, acceptance (about 6-10 claims each) | 25-40 min | 24 | 10-16 |
| Questions with gold answer kind, binding, evidence documents, interval mode and the rule used | 10-15 min | 48 | 8-12 |
| Self-check pass: consistency of world script, documents and gold; quota check | — | once | 3-4 |
| **Primary author total** | | | **37-57 h** |
| Second annotator: 20% of documents (5) annotated independently | 30-45 min | 5 | 3-4 |
| Adjudication of disagreements with the primary author | — | once | 2-3 |
| **Second annotator total** | | | **5-7 h** |

For one primary author that is roughly **5-7 working days**, plus about **1 day** for the second annotator.

## Eight-document mini-pilot (after the trial)
**8 documents and 16 questions**, one organisation pair plus a subcontractor. It covers each phenomenon at
least once:
- reinstatement
- a late correction
- conflicting reports
- a multi-party approval
- a moved deadline
- an unknown answer
- a negative control

| Task | Hours |
|---|---|
| Guidelines and examples | 2-3 |
| Smaller world script | 2-3 |
| 8 documents | 3-5 |
| Gold for 8 documents | 3-5 |
| 16 questions | 3-4 |
| Self-check | 1-2 |
| **Primary author total** | **14-22 h** (about 2-3 days) |
| Second annotator: 2 documents plus adjudication | 2-3 h |

**What the mini-pilot tells us before committing to the full split:**
- the real minutes per document and per question
- whether the guidelines are clear enough (inter-annotator agreement on the double-annotated documents)
- how much of the gold GUPI's schema can express (schema coverage)
- whether the question families and interval modes are unambiguous

If agreement is low (role-filled-claim F1 below 0.8, or kappa below 0.6), the guidelines are revised before
the full split.

## Notes
- Gold quality matters more than volume. A smaller, well-adjudicated split gives more trustworthy results
  than a larger rushed one.
- The held-out author must not read GUPI's code, schema or rule patterns; the guidelines must be enough.
- Writing in several fictional voices (director, engineer, external vendor) takes longer, and is what makes
  the documents realistic; the ranges above allow for it.
- The implementer can write the development split (16 documents, 32 questions) in parallel; it is not
  independent and is never used as held-out data.
