# Phase 7A coverage analysis: domain, language, context

**What is measured and what is estimated:**
- **Measured:** extractor outputs.
- **Estimated:** everything that depends on the annotations. They are one annotator's labels on a small
  development sample.
- **Intervals:** 95% Wilson intervals. With these denominators they are wide, so read them as orders of
  magnitude, not rates.

## Domain coverage (what the extractor attempts)
**`rules:v2` covers two relations:**
- **employment:** join, start, hire, promote, leave, works or has worked at, negations, plans
- **reporting:** reports or has reported to, stopped reporting, negations

It extracts nothing else.

| Representative sample (60 turns) | Count | Share |
|---|---|---|
| turns with any potentially useful memory | 28/60 | 46.7% (34.6–59.1%) |
| turns with a supported (A) fact | 1/60 | 1.7% (0.3–8.9%) |
| turns with only borderline or unsupported facts | 27/60 | |
| relevant assertions | 39 | A 1, A? 7, B 31 |

**In the targeted work-vocabulary sample (40 turns):**
- **Turns:** 34 have something, but only 7 hold an A fact.
- **Assertions:** A 7, A? 10, B 29, out of 46.

**What the B facts are:**
- **LoCoMo:** hobbies and art, family, events, plans, identity and activism.
- **LongMemEval:** purchases, shopping habits, residence, plans, interests, and, in assistant turns, world
  knowledge (8 of the 46 targeted assertions).

**How these datasets differ from the material GUPI was built on:**
- **LoCoMo:** two friends talking about their lives.
- **LongMemEval:** a user talking with an assistant about tasks and interests.
- **Organisational facts are rare in both,** and named employers rarer still. The sample's only clean A fact
  with a named organisation is one LongMemEval user stating a new job title.

## Linguistic coverage (alternative ways of saying supported things)
**Probes v1** (53 frozen probes): of the 48 expressions that should give a candidate, `rules:v2` matched
15:
- **The supported phrasings:** all 11 matched.
- **Variations:** 4 of 37 matched.

**Missed groups:**
| Group | Missed | Examples |
|---|---|---|
| other verbs | 11 | began working for, took a job at, came on board, was appointed, quit, resigned, stopped working for, was let go, is employed by, has left, started my new job |
| sentence structure | 12 | leading time ("In March 2025, …"), lead-ins ("So, …"), trailing or embedded clauses, apposition, "is the CTO at", possessives, inverse "manages", "boss", "Sorry, I meant …", "I've been at X since" |
| dates | 2 | ISO dates, "five months ago" |
| names and casing | 4 | a lowercase organisation, three-word names, "&", an all-lowercase sentence |
| first person | 2 | "I report to", "My manager is" |

**Probes v2** (the brief's ten sentences, probe-results.json):

| Probe | Expression | Result |
|---|---|---|
| n01 | "joined … in March 2025" | **match**: start, March 2025, direct, certain, formed |
| n02 | "started working for" | missed |
| n03 | "has worked at … since March 2025" | **match**: held-since March plus holds now, formed |
| n04 | "Since March 2025, Nora has been with" | missed |
| n05 | "Nora's been at … since March" | missed |
| n06 | "She joined them last spring" | correctly nothing |
| n07 | "I started working there last March" | correctly nothing |
| n08 | "Nora told me she joined …" | missed (the lowercase pronoun defeats the reported-speech pattern) |
| n09 | "Apparently Nora started at …" | **match**: commitment probable, so sent to review |
| n10 | "Correction: … in April, not March" | **match**: start April, correction linked to the earlier statement, sent to review |

**Where it matched,** the temporal meaning, attribution and certainty were kept distinct, as intended.

**On the sample:** every A assertion fails on phrasing. Most often the employer is unnamed ("my job", "a
temp job", "an internship"), which no pattern accepts and the contract cannot represent without a
placeholder.

## Context resolution
- **Cross-turn needs:** 24 of 85 annotated assertions (28.2%, 19.8–38.6%) need an earlier turn, and 26 are
  implicit.
- **Pronouns:**
  - **What rules:v2 resolves:** only the author's "I".
  - **What else happens:** other pronouns are either not matched or, when capitalised, taken as names
    (defect D1).
- **Corrections:** these resolve within a thread (probe n10, 6B p05).
- **Context is not the binding constraint:** in this sample no in-domain assertion fails *only* because
  of context. Domain or phrasing stops it first.

## Formation
**Formation was never reached on benchmark text** (0 candidates). On probes it behaved as documented:
- plain assertions formed
- hedged and corrected statements sent to review
- negations formed as negative claims

**No formation failure is counted as an extraction failure, or the other way round.**

## Extraction ceilings (estimates)
**The definitions:**
- **Current rules:** what `rules:v2` as it stands could recognise without a wider domain or cross-turn
  references.
- **Improved rules:** add reasonable vocabulary and syntax within employment and reporting, keeping the
  contract (named participants only).
- **Improved rules plus a placeholder employer:** a contract change, so that "lost my job" can be held.
- **Broader:** every assertion about participants that an expanded ontology plus context-aware extraction
  could hold. This excludes world knowledge.

| Ceiling | Representative (39 assertions) | Targeted (46) | Phase 2 held-out (12 gold claims, independent) |
|---|---|---|---|
| current rules | 0/39 = 0% (0–9.0%), measured | 0/46 (0–7.7%), measured | 5/12 = 41.7% (19.3–68.0%), measured in 6B/6D |
| improved rules, same contract | 1/39 = 2.6% (0.5–13.2%) | 1/46 = 2.2% (0.4–11.3%) | about 10/12 = 83% (55–95%) |
| improved rules plus a placeholder employer | 8/39 = 20.5% (10.8–35.5%), if own-business counts | 17/46 = 37.0% (24.5–51.4%) | 10/12 |
| broader | 38/39 = 97.4% (86.8–99.5%) | 38/46 = 82.6% (69.3–90.9%) | 12/12 |

**Assumptions:**
- **Improved rules on Phase 2:** all five in-domain misses there have phrasings a rule could cover:
  - "Welcome X, who joined"
  - "is the Product Lead at"
  - "X's manager is Y"
  - "Update:"
  - "Noah manages Kim"
- **Caveat on that Phase 2 figure:** those messages have been seen, so 10/12 is an upper bound for a rules
  update, not a measurement.
- **"Broader" is representability, not recoverability.** It assumes an ontology for hobbies, plans,
  purchases and residence that GUPI does not have. It says nothing about how accurately anything would
  extract them.
- **Both samples come from the development splits** and are small. The targeted sample over-represents
  work talk by design.

**Uncertainty:**
- **Where the annotation is a judgement:** the borderline A? facts (own business, an unnamed institution).
- **How much it moves:** the improved-rules-plus-placeholder figure moves by 7 (representative) or 10
  (targeted) depending on that call.
