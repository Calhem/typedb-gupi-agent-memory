# Failure attribution (failure modes A–F)

**Origins of each failure:**
- **model:** the extraction chose badly within the rules
- **instructions:** the frozen instructions led to it
- **format:** format 1.1 cannot express it
- **validator / formation:** GUPI's checks or policy
- **scoring or gold:** the evaluation's own conventions

**What is observed and what is a hypothesis:**
- **Observed:** facts from the source text, the raw responses, the frozen documents or the code.
- **Hypotheses:** labelled as such.
- **The gold:** not quoted. Where a judgement depends on it, it goes to the adjudicator (package item numbers in
  brackets).

## A. Statement objects: free text versus a longer predicate
**What was observed** (items 1–4, 6–8):
- **The pattern:** in 7 of the 9 statement candidates, the model gave the shortest verb as the predicate and put
  the rest in `object_text`.
  - "accessed" plus "the Saltmarsh Energy network"
  - "entered" plus "the Saltmarsh Energy network"
  - "will revoke" plus "the authorisation of Teverin Holdings"
  - "has opened" plus "an internal investigation"
  - "is operated by" plus "the same team as the COPPER MOTH group"
- **The instructions:** they ask for exactly this. "The shortest verb phrase from the text that states the
  relation"; a descriptive object "goes in `object_text`"; and the worked example ("has suspended" plus
  "Calloway Marine's berth permit").
- **"Saltmarsh Energy network":** the instructions allow "a named system" as a participant, and give no rule for
  a name embedded in a description ("the Saltmarsh Energy network", "the authorisation of Teverin Holdings").

| Kind of mismatch | Cases | What it means |
|---|---|---|
| equivalent representation | accessed / entered / will revoke + object_text | the proposition survives in predicate-text + object-text; the scorer's exact-predicate and participant rules do not see it. **Scoring convention** (pending items 1, 3, 4, 6) |
| loss of a material qualifier | has opened + "an internal investigation", object participant Dmitri Sava | "into" is lost: the structure no longer says how Dmitri Sava relates to the investigation. **Format** (no link between object participant and object text) |
| genuine semantic distortion | is operated by + object participant COPPER MOTH | the role structure states a different relation (B). **Model + format** |

**The smallest improvement** (a proposal, not implemented): add one format rule. **When a statement has an object
participant, it must be the direct object of the predicate-text, or the predicate-text must include the linking
words** ("has opened an internal investigation into"). Check structurally that the object participant's surface
does not lie inside `object_text`. That would have flagged B. Proposals R1 and R7.

## B. LANTERN-7 / COPPER MOTH
**What was observed:**
- **The source:** "is operated by the same team as the COPPER MOTH group".
- **The structure:** subject LANTERN-7, predicate-text "is operated by", object participant COPPER MOTH.
- **The object text:** "the same team as the COPPER MOTH group".
- **So:** the model turned *shares an operator with* into *is operated by* in the roles, and kept the correct
  wording in free text.

**Could GUPI detect it?** Not as built.
- **Structural validity:** every check passed, because each string is grounded in the evidence span and the roles
  are legal for a statement.
- **Semantic faithfulness:** "do the roles plus the predicate reproduce the source proposition?" is checked
  nowhere.
- **The one structural signal:** the object participant's surface occurs inside `object_text`. That is detectable
  without semantics.
- **What prevented formation:** only the source's hedge ("we assess with moderate confidence").

**The cause:** model, plus format. No semantic validator is proposed. R1 gives the structural rule, and R2 a
reviewer cue.

## C. Identity ambiguity
**What was observed:**
- **The format rule:** "`is_pronoun_or_vague`: true for … a name you cannot tie to one individual. GUPI then sets
  the assertion aside rather than guess an identity. That is the correct outcome, not a failure."
- **The instructions:** "never add a surname, a company or a role the text does not give".

| Case | Source | What the model did | Analysis |
|---|---|---|---|
| X3-09 (item 15) | "… Victor Hale, approved payments … Hale denies the allegations." | marked "Hale" vague; the denial was set aside | "Hale" follows "Victor Hale" in the same passage. Writing "Hale" (not vague) would create a separate referent "Hale", because referents are scoped by surface; writing "Victor Hale" would break "write what the text writes". **Format/instructions**: no way to say "this surname refers to that earlier full name" |
| X3-20 (item 14) | "According to Teverin Holdings, Victor Hale left … Mira Solberg, Hale's lawyer, says Hale was dismissed …" | marked "Hale" vague; the lawyer's account set aside | as X3-09; also the first account was marked an allegation (commitment unknown), so it went to review |
| X3-29 (item 11) | "There are two Daniel Reyes on the vendor list: Daniel Reyes at Quillon Analytics …, and the other Daniel Reyes works for Saltmarsh Energy." | abstained on both | **S8:** two same-named people in one conversation share one referent. Extracting both would have recorded one "Daniel Reyes" employed by both organisations, an unsupported merge. Abstention avoided an error GUPI cannot otherwise prevent |

**Identity guesses are not rewarded here.** Whether the gold should expect these assertions is for the
adjudicator, and the protocol does not count a guess as correct just because it matches an annotation.

**Hypothesis:** the surname cases are recoverable without guessing, through a within-passage coreference field
(R5). The Daniel Reyes case is not recoverable until S8 is addressed.

## D. Former employment (X3-09)
**What was observed:**
- **The source:** "Teverin Holdings' former treasurer, Victor Hale" (document date 2025-07-18).
- **The candidate:** employment, title "treasurer", **no time**.
- **Formation:** formed.

**The evidence semantics:** "former" means the employment had ended by the document date. Start and end are
otherwise unknown. In valid-time terms, the end lies in an unbounded window up to the document date:
`to_latest = 2025-07-18`.

**What GUPI stored:** no valid time.
- **Not stronger than the source:** `temporal.holds_at` returns UNKNOWN for every date, never TRUE, and ADR 0003
  says a missing end "is not the same as still true".
- **But weaker than the source:** "did it hold after 2025-07-18?" should be FALSE, but is UNKNOWN. And the stored
  title reads "treasurer", not "former treasurer".

**The impact on historical answers:**
- **No false current answer.**
- **A lost negative:** the claim cannot help end a spell. An answering path that joined it with other claims
  (answering v2, "presumed" periods) could treat it as evidence of an open period.
  - *Hypothesis, not tested:* whether answering v2 ever presumes across a timeless claim needs a test, which is
    R6.

**The cause:** format. There is no time kind for "ended by the document date". The parser and time reader are
correct for what they receive.

## E. Corrections and bare retractions
| Case | Source | Observed | Cause |
|---|---|---|---|
| X3-16 (item 16) | "Gareth Lowe joined Teverin Holdings in June 2025." (thread turn 2, a different author from turn 1's "in August 2025") | extracted correctly; no correction marked | **format:** a correction needs a `cue`, and there is none. A contradiction between two authors is not a correction by either. GUPI's answering layer already reports competing starts (answering v2, Q9). **Scoring/gold:** whether a cue-less contradiction should be expected from the extractor is for the adjudicator |
| X3-17 (item 17) | "Sorry, ignore what I said yesterday about Gareth, I mixed him up with someone else." | no assertion; reported as `insufficient-evidence` ("no assertion to carry a correction field") | **format:** 1.1 attaches a correction only to an assertion, and an assertion needs a participant and a claim. The problem report is not stored (S1-like). The retracted earlier claim stays formed and unflagged |

**The minimum requirements for a format extension** (described only; there is no format 1.2):
- **What it must hold:**
  - a correction record with no assertion: `{kind: retracts | corrects, cue, evidence}`, grounded like any other
    string, plus an optional `about` surface ("Gareth"), marked vague when it is
- **What GUPI does with it:**
  - resolves the target by the existing thread rules, or leaves it unresolved
  - never supersedes anything automatically (L2, L3)
  - routes the record to review, and flags the candidate target claims "retraction pending"
- **Compatibility:** additive. Format 1.1 responses stay valid, and 1.1 parsers ignore the new outcome.

The new outcome also needs a stored, reviewable record, which is the S1 gap.

## F. Claimant kind (3/6)
**What was observed:**
- **The 3 misses:**
  - X3-06 "According to Celia Brandt, …" (item 18)
  - X3-08 "The Ledger Courier reported that Anders Moll told investors …" (item 19)
  - the X3-09 employment, where the frozen scorer counts the candidate's claimant itself as invented
- **The frozen rule:** "`person` or `organisation` only when the passage establishes it; otherwise `unknown`". In
  X3-06 and X3-08 the passage gives only the name: no pronoun, title or role.
- **Where the passage does establish it:** the model used the kind. "Mira Solberg, Hale's lawyer" is a person,
  and "Teverin Holdings" an organisation.

**The assessment:** consistent with the rule, so this is not a failure to use explicit evidence. **No kind should be
inferred from a name alone.** Whether the gold should expect `person` here is for the adjudicator. The disagreement
is between the gold and the rule, not between the model and the rule.

## Summary: where the failures originate
| Origin | Cases |
|---|---|
| model (within the rules) | B (the predicate split that changed the relation); X3-23 (extracting a question it could have left out); X3-07 (marked the employer inferred: a judgement call, item 10) |
| instructions | A (shortest predicate + object_text), F (kind rule), C (no surname resolution) |
| format 1.1 | A/B (no link between object participant and object text), D ("former"), E (bare retraction, cue-less contradiction) |
| validator / formation | none rejected or formed wrongly by their own rules; **gap:** no faithfulness check; retraction and problem reports not stored |
| known GUPI limitations | S8 (X3-29), L4 (X3-27/28 counted as two supporting claims), L5 (X3-07: inferred refused rather than reviewed) |
| scoring or gold | exact-predicate rule (A), name normalisation ("invented entity", B), gold coverage of questions (X3-23); the disputed gold items go to adjudication |
