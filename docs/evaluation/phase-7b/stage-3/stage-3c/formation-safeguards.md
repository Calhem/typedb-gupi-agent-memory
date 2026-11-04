# Formation safeguards: the 30 decisions reconstructed

**How:** the frozen Stage 3B formation was re-run privately (`gupi-stage3-private/stage3c/reconstruct_formation.py`),
which calls `stage3.formation` in a disposable TypeDB 3.14.1 database.
- **The result reproduces Stage 3B exactly:** 17 formed, 4 review, 9 withheld, 0 rejected, 0 store rejections, 0
  failures, 0 supersessions.
- **Every decision and its reason** is recorded privately.

## The decisions, by the rule that decided them
| Rule in `form.decide` (order of application) | Candidates | Examples (source wording) |
|---|---|---|
| non-actual modality → withheld | 4 | question "Is Dmitri Sava still at …?"; planned "is about to be acquired by" (rumour); planned "might be moving to"; conditional "If … misses …, … will revoke" |
| copy of an existing claim → withheld | 1 | the second forward of Anika Torvald's message |
| time only "at some instant in a window" → withheld | 4 | four single-day events ("on 22 July 2025 … accessed", "fined … on 10 June 2025", …) |
| hedged → review | 3 | "The complaint alleges …" (allegation → commitment unknown); "We assess with moderate confidence …"; "According to Teverin Holdings, Victor Hale left …" (marked allegation) |
| stated correction → review | 1 | "Correction: Jonas Ekberg started … on 14 July 2025" (target resolved in the thread) |
| none of the above → formed | 17 | including the three formed severe errors |

**Before formation,** the interface (`model:candidate-v1.1`) set aside 18 reported problems:
- **9 vague or pronoun references:** never given an identity
- **2 inferred assertions:** refused (L5)
- **6 insufficient evidence**
- **1 no relevant assertion**

Grounding passed 30/30, and the injection line in X3-30 produced no candidate.

## Which safeguards worked
| Safeguard | Evidence |
|---|---|
| a question, plan or condition is never formed | 4/4 withheld, including the extracted question (severe error 2) |
| copies are not independent attestations | the repeated forward was withheld; no copy was formed |
| hedges and allegations go to review | 3/3. This is what stopped the LANTERN-7 distortion |
| corrections go to review; unresolved targets stay unresolved | X3-12 went to review; nothing was superseded |
| day-only events are not made into periods | 4/4 withheld |
| no invented identities | vague names and pronouns set aside; inferred assertions refused |
| text addressed to automated systems is data | the X3-30 instruction line produced no candidate |
| grounding | every string is in its evidence span (30/30) |

## Which safeguards failed, or do not exist
| Case | What happened | Why no safeguard caught it |
|---|---|---|
| role structure differs from the source (X3-19; X3-27/28 lose "into") | X3-27/28 formed; X3-19 was stopped by the hedge alone | no rule relates the object participant to the predicate or the object text; validation is structural |
| disputed attribution scope (X3-09 employment) | formed, claimant "The complaint" | whether an appositive belongs to the reporter or the author cannot be decided from the structure |
| "former" with no time (X3-09) | formed timeless | the format cannot express "ended by the document date"; formation has no reason to hold it (ADR 0003 makes it UNKNOWN, not TRUE) |
| bare retraction (X3-17) | nothing to decide; the retracted claim stays formed | no candidate is produced; problem reports are not stored |
| same claimant via two authors (X3-27/28) | both formed | wording differs, so the F1 copy detection (L4) does not match; not a copy under the current definition |
| unsupported employer inference (X3-07) | refused by the interface, not formed | worked as designed (L5); whether the employer was in fact stated is for the adjudicator |
| forwarded evidence (X3-24/25) | first formed as forwarded (claimant the sender), second withheld | worked |

## The three formed severe errors: what could have prevented each
| | Better instructions | Format constraint | Existing validation | Evidence review | Formation policy |
|---|---|---|---|---|---|
| X3-09 attribution | could state a rule for appositives inside reported clauses | – | no | yes (a reviewer reading the source) | a rule to send reported claims on an allegation clause to review would catch it, at a cost in review volume |
| X3-27 / X3-28 lost "into" | could require the linking words in the predicate when an object participant is given | yes (R1) | no | yes | no |

**Undetectable without returning to the source text or a semantic check:**
- **Attribution scope** (X3-09).
- **A changed relation,** when the object participant is not inside `object_text`. X3-19 is detectable structurally
  only because it is inside.
- **A predicate that drops a preposition** (X3-27/28), unless the format forbids an object participant outside the
  predicate's direct object.

**Structural validity is not semantic support.** Every one of these candidates was structurally valid.
