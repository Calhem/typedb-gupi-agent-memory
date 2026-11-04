# Proposed remediation (design only; nothing implemented)

**The ranking:** by correctness impact, putting first whatever prevents unsupported definitive claims. **None of
these needs adjudication to be justified**, because each rests on source text, frozen documents or code. The
evaluation-only items (R7, R8) improve measurement, not GUPI. Each needs the owner's approval.

## 1. Essential correctness fixes
### R1. Tie a statement's object participant to its predicate
| | |
|---|---|
| Observed failure | role structures that misstate (X3-19: "is operated by" + COPPER MOTH) or garble (X3-27/28: "has opened" + Dmitri Sava) a supported proposition; two of these were formed |
| Root cause | format 1.1 lets `predicate`, the object participant and `object_text` be chosen independently; the instructions demand the shortest verb phrase |
| Evidence | raw responses; the instructions' worked example; all three passed every validator |
| Proposed change | (a) a format rule: when an object participant is given, `predicate` must contain every word between the subject and the object participant that states their relation (so "has opened an internal investigation into", "is operated by the same team as"); (b) a structural check in the interface: refuse (`validation`) an object participant whose surface lies inside `object_text`, or whose surface is not adjacent to the end of `predicate` in the evidence |
| Expected benefit | the role structure says what the source says; X3-19-type errors become structural failures instead of review-only catches |
| Compatibility | a format 1.1 minor rule change (1.1 responses that violate it become `validation` outcomes, so stricter, not breaking for valid ones); stored claims unchanged; the scorer's exact-predicate rule then matches the gold convention |
| Regression tests | the three Stage 3B shapes as synthetic fixtures (not corpus text); a valid "has suspended" + non-entity object still accepted; a participant inside object_text refused |
| Risk of new unsupported assertions | none added; recall may fall when the model does not comply (a refusal, not a wrong claim) |

### R2. A bare retraction must reach review
| | |
|---|---|
| Observed failure | X3-17: "ignore what I said yesterday about Gareth" left the retracted claim formed and unflagged |
| Root cause | format 1.1 carries corrections only on assertions; problem reports are not stored (S1) |
| Evidence | raw response (`insufficient-evidence`, "no assertion to carry a correction field"); formation decisions |
| Proposed change | an assertion-less correction outcome (failure-attribution.md E): grounded `cue` and `evidence`, optional vague `about`; GUPI resolves a target in the thread or leaves it unresolved, stores it as a reviewable record, and marks candidate targets "retraction pending" in answers; never supersedes automatically |
| Expected benefit | a retraction can no longer vanish; answers that rest on a possibly retracted claim say so |
| Compatibility | additive (a new outcome); needs a stored record type (schema addition) and an answer note; 1.1 responses unaffected |
| Regression tests | synthetic thread: claim, then bare retraction → target flagged, nothing superseded; unresolved target → review; existing D3 and L2/L3 tests unchanged |
| Risk | none of new assertions; a false "retraction pending" flag if the cue is misread (a review, not a claim) |

### R3. Send reported claims inside an allegation clause to review
| | |
|---|---|
| Observed failure | X3-09: an employment drawn from inside "The complaint alleges that …" formed as certain |
| Root cause | the allegation flag was set on the statement but not on the employment drawn from the same clause; formation looks only at the candidate's own commitment |
| Evidence | raw response (the statement carries `allegation: true`, the employment does not); formation reason "an asserted actual condition or event" |
| Proposed change | in the interface: any assertion whose evidence span lies inside another assertion's allegation span inherits `allegation` (so commitment unknown → review). No new inference: it is the same span |
| Expected benefit | facts embedded in allegations are reviewed, whichever reading of attribution is right |
| Compatibility | no format change; more review volume |
| Regression tests | synthetic "X alleges that Y's former Z, W, did …" → both review |
| Risk | none of new assertions; more reviews |

## 2. Extraction-quality improvements
| # | Failure | Proposed change | Benefit | Compatibility | Risk |
|---|---|---|---|---|---|
| R4 | "former" lost (X3-09) | a time kind `ended-by-document` (or `end` with the phrase "former" read as the window up to the document date) | the claim stops supporting any date after the document; answers become FALSE instead of UNKNOWN | additive time kind; the time reader gains one rule | an over-broad reading of "former" (e.g. "former colleague" of a still-existing relation); tests must cover it |
| R5 | surname references set aside (X3-09, X3-20) | a within-passage coreference field: `same_as` naming an earlier participant surface **in the same passage**; GUPI links them only when the full name occurs exactly once | assertions about "Hale" become extractable without inventing a name | additive field | wrong links if the passage has two Hales; the "exactly once" rule is the guard |
| R6 | timeless claims in answering v2 | a test that a timeless claim never contributes to a presumed period | confirms or rules out the D hypothesis | test only | none |

## 3. Scoring and evaluation improvements (evaluation tooling only)
| # | Issue | Proposed change |
|---|---|---|
| R7 | exact-predicate and surface matching turn equivalent forms into partials or "invented entity" | record adjudicated accepted alternatives per gold assertion, and score predicate-text + object-text together against the gold predicate; name containment ("COPPER MOTH" in "COPPER MOTH group") reported as a separate class, not "invented entity" |
| R8 | the transcript audit cannot read desktop transcripts | de-duplicate tool calls by id, and allow-list the app's turn tools by exact name; keep the frozen audit and its result unchanged, and version the new one |
| R9 | gold coverage of questions and cue-less contradictions | decide in the annotation contract whether questions and cross-author contradictions are expected from the extractor |
| R10 | one corpus, one author, one model family | a second corpus written and annotated by a person outside the project, before any adoption decision |

## 4. Deferred
**These are left for later:**
- **S8,** referent scoping, which is the X3-29 case. It needs identity design, and abstention is the safe behaviour
  until then.
- **L4,** paraphrase-tolerant copy detection (X3-27/28).
- **L5,** sending inferred assertions to review instead of refusing them (X3-07). That waits for adjudication of
  item 10.
- **A semantic faithfulness validator** (a second model or an entailment check). It is not proposed: R1–R3 remove
  the observed cases structurally.

**On X3-30:** no change is proposed for the injection-like line. It was handled correctly.
