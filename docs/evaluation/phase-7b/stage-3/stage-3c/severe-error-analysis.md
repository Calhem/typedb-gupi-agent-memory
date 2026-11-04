# The five Stage 3B severe errors

**Sources:** the frozen definitions (scoring/README.md), the raw responses, the stored candidates and the
reconstructed formation decisions.
- **The gold interpretations** are recorded privately (`gupi-stage3-private/stage3c/severe-errors-with-gold.md`),
  not here.
- **Who wrote this:** the gold's author, Claude. So every classification that turns on whether the gold is right
  is **unresolved pending adjudication**. No label is cleared here.

| # | Passage (package item) | Frozen label | Formation | Final classification |
|---|---|---|---|---|
| 1 | X3-19 (5) | invented entity | review (hedged) | unresolved pending adjudication; a real distortion in the role structure (below) |
| 2 | X3-23 (13) | unsupported claim | withheld (question) | unresolved pending adjudication (gold coverage); can never be formed |
| 3 | X3-09 (9) | invented claimant | **formed** | unresolved pending adjudication |
| 4 | X3-27 (7) | unsupported definitive assertion | **formed** | unresolved pending adjudication |
| 5 | X3-28 (8) | unsupported definitive assertion | **formed** | unresolved pending adjudication |

**Confirmed formed severe errors: between 0 and 3,** until items 7, 8 and 9 are adjudicated.

## 1. X3-19: "operated by the same team as"
- **The source:** "We assess with moderate confidence that LANTERN-7 is operated by the same team as the COPPER MOTH
  group."
- **The candidate:**
  - **Roles:** subject `LANTERN-7`, **object participant `COPPER MOTH`**.
  - **Text fields:** predicate-text `is operated by`; object-text `the same team as the COPPER MOTH group`.
  - **Commitment:** probable.
- **Formation:** review (hedged by the source).
- **Does it change the meaning?** **In the role structure, yes:** subject, predicate and object participant read
  "LANTERN-7 is operated by COPPER MOTH". That converts "shares an operator with" into "is operated by". Read
  together, the predicate-text and object-text are faithful.
- **The causes, all three contributing:**
  - **extraction:** the predicate was split before "the same team as"
  - **representation:** format 1.1 does not tie the object participant to the object text
  - **scoring:** "COPPER MOTH" is a substring of the source, so the label "invented entity" comes from name
    normalisation, not from an entity that isn't in the text
- **The downstream risk:** if a reviewer approved it, a query by role ("who operates LANTERN-7?") would return
  COPPER MOTH. It was caught only because the source was hedged. **A certain version of the same sentence would
  have been formed.**

## 2. X3-23: a question extracted
- **The source:** "Is Dmitri Sava still at Morrow & Fane? Ruth says he left, but his email still works."
- **The candidate:** employment Dmitri Sava at Morrow & Fane, `modality: question`, commitment unknown.
- **Formation:** withheld. `form.decide` withholds every non-actual modality before any other rule, so this cannot
  be formed.
- **Does it change the meaning?** No: it is recorded as a question.
- **The cause:** the frozen instructions say questions "take their modality", which invites extracting them. The
  gold doesn't annotate the question, so the scorer counts it unsupported. Whether the gold should cover it is an
  adjudication question.
- **The downstream risk:** none.

## 3. X3-09: "The complaint alleges that … former treasurer, Victor Hale, …"
- **The candidate:**
  - **The claim:** employment Victor Hale at Teverin Holdings, title `treasurer`, certain, no time.
  - **The attribution:** `reported`, claimant "The complaint" (`unknown`).
- **Formation:** formed ("an asserted actual condition or event").
- **Does it change the meaning?** Two things, kept apart:
  - **Attribution:** the appositive sits inside the clause governed by "alleges", so its scope is ambiguous in the
    source. The gold reads it differently, and that is item 9.
  - **"Former" is lost** under either reading. That loss is separate from the severe label (failure-attribution.md
    D).
- **The causes:**
  - **extraction or attribution:** the scope ambiguity
  - **representation:** "former" can't be expressed
- **The downstream risk:**
  - **Attribution:** low. The candidate names a weaker source than an author's direct statement, so it doesn't
    strengthen the claim.
  - **Time:** the claim has no valid time, so GUPI answers "does it hold at v?" with UNKNOWN, never TRUE
    (`temporal.holds_at`).
  - **The title:** stored without "former".

## 4 and 5. X3-27, X3-28: "has opened an internal investigation into Dmitri Sava"
- **The sources:**
  - "Celia Brandt told me that Morrow & Fane has opened an internal investigation into Dmitri Sava." (Lena
    Haverford)
  - "Celia Brandt says Morrow & Fane has opened an internal investigation into Dmitri Sava." (Ilka Brennan)
- **The candidates:**
  - **Roles:** subject `Morrow & Fane`, object participant `Dmitri Sava`.
  - **Text fields:** predicate-text `has opened`, object-text `an internal investigation`.
  - **Attribution:** reported by Celia Brandt (`unknown`); certain.
- **Formation:** both formed.
- **Does it change the meaning?** The proposition is supported by the source. What is lost is **"into"**, the
  relation between the investigation and Dmitri Sava.
  - **What the structure says:** "Morrow & Fane has opened Dmitri Sava".
  - **What the evidence span says:** the full sentence, and it is stored.
- **The causes:**
  - **representation:** there's no link between the object participant and the object text
  - **scoring:** the exact-predicate rule
  - **instructions:** the split follows the frozen instructions' own worked example ("has suspended" plus
    object-text "Calloway Marine's berth permit"), and their rule "the shortest verb phrase"
- **The downstream risk:**
  - **The structure:** a role-based answer is malformed rather than false.
  - **Corroboration:** the two reports have the same claimant but different authors. Both are formed. Formation
    recorded no copy (the wording differs), so a count of supporting claims would show two, from one originator.
    This is the known limitation L4, not a severe error under the frozen definitions.

## What the five have in common
**None of the five is an invented participant or an invented claim about something the source does not say.**
- **Three (1, 4, 5):** structured roles that can misstate or garble a supported proposition.
- **One (3):** a genuine ambiguity of attribution scope.
- **One (2):** a correctly marked question.

**The structural validators accepted all five, as designed.** Detecting 1, 4 or 5 needs either:
- a format constraint tying the object participant to the object text, or
- a check against the source text

None of the current checks tests faithfulness. (formation-safeguards.md and proposed-remediation.md.)
