# Phase 6B: `rules:v2` candidate extraction, first run

Date: 2026-11-03. Offline; no TypeDB, no LLM. Reproduce with:

    uv run python -I -m gupi.formation.evaluation

Raw results: `phase-6b-extraction-first-run.json`.

## Protocol
1. **The evaluation set was written and committed first** (`a5a1671`): 32 passages, frozen, in
   `tests/fixtures/formation/eval-v1.json`. Only after that was `rules:v2` written (`75a9750`). Its
   unit tests use their own sentences.
2. **One evaluation invocation before this run crashed** on a regex compile error, before producing any
   output. No results were seen. After the fix, the extractor was exercised only on the unit-test sentences.
3. **These results are the first run, unchanged.** The extractor has not been changed since.
4. **Measures:**
   - **Precision** is matched / extracted, and **recall** is matched / expected, reported separately.
   - **A match** requires the same claim type, participants and polarity.
   - **Other fields** are scored only on matched pairs.
   - **Correct rejections** (nothing extracted from a passage with nothing in the domain) are counted apart.
     They are never extracted claims.

## Results
### The frozen 6B set (32 passages)
| Measure | Result |
|---|---|
| Precision | **30/30 = 1.00** |
| Recall | **30/31 = 0.97** (the miss: "He rejoined in June", a pronoun) |
| Correct rejections | 5 of 5 passages with nothing in the domain |
| Modality, commitment, attribution mode, asserted by, relations (corrects, repeats) | 30/30 each, of matched |
| Time kinds and phrases | 12/30 of matched (see below) |

**About the 18 time "errors":**
- **16 are a systematic convention difference.** For a present-tense statement, the extractor adds a
  `holds-at` reading at the observation time, with the verb ("works", "has reported") as its phrase. The gold
  lists only explicit time phrases. These readings are intended: they are what makes "works at" true *now*.
  The frozen scorer counts them as errors, and that is left as it is.
- **2 are unread phrases kept as written:** "later this year" and "Smarch 2025", where the gold lists no time.
- **Not one is a wrong time kind:** no `start` where `holds-since` was expected, and no `holds-since` where a
  start was expected. That includes "Since March, ..." against "From March, ...".

**This set flatters the extractor.**
- **Who wrote it:** the implementer, just before the extractor, with its planned scope in mind.
- **What follows:** its phrasing ("According to X,", "X told me that", "might join", "isn't with X
  anymore") overlaps the patterns closely. It shows that the intended behaviour works. It does **not**
  estimate how well extraction generalises.

### An independent check: the Phase 2 conversations
These conversations were written in Phase 2, before `rules:v2` was designed. The held-out split was never
used to write either rule extractor.
- **What is compared:** type, participants and polarity only. That gold encodes "since June" as a start,
  so time kinds are not compared.
- **The baseline:** `rules:v1`, run through the existing contract validator with the same matching.
- Generic `statement` claims are outside v2's domain, and count as misses for both.

| Split | Extractor | Precision | Recall |
|---|---|---|---|
| held-out (independent) | rules:v2 | 5/5 = 1.00 | **5/12 = 0.42** |
| held-out (independent) | rules:v1 | 5/5 = 1.00 | 5/12 = 0.42 |
| development (rules:v1 was written on it) | rules:v2 | 8/8 = 1.00 | 8/12 = 0.67 |
| development | rules:v1 | 10/10 = 1.00 | 10/12 = 0.83 |

**On independent text, v2 finds as much as v1, no more,** and is just as precise.
- **Where v2 gains:**
  - "Mia Chen left Lumen Labs last month": v1 requires "in" or "on" before the date
  - "Kim has worked at Vector since 2022"
- **Where v2 loses:**
  - "Update: ..." and "Quick intro: ...": v2 recognises only "Correction:" as a prefix
  - "X is the Product Lead at Y" and "X is a Staff Engineer at Y": I left out v1's "is <title> at"
    pattern, in error
- **Both miss:**
  - "Welcome Jonas Berg, who joined ...", because of the leading word
  - "Lena Fischer's manager is Raj Patel"
  - "Noah manages Kim"
  - every pronoun subject
  - the generic statements

## Known failures (not fixed: the run is reported as it is)
1. **Generic prefixes** other than "Correction:" ("Update:", "Quick intro:") stop a match.
2. **The "is <title> at <organisation>" phrasing is missing** (present in v1).
3. **Possessive and inverse phrasings** ("X's manager is Y", "Y manages X") are missing.
4. **A leading word before a relative clause** ("Welcome X, who joined ...").
5. **Pronouns and implied participants.** Only the author's "I" is resolved.
6. **Unreadable time phrases** ("next month", "last spring", "later this year") are kept without a window.
   This is by design, but it means the valid time is unknown.
7. **A correction can only target an earlier candidate in the same thread.** Correcting an existing claim
   needs a memory lookup, which is 6C.
8. **"Probably" and "I think" are mapped to `probable`** by a fixed table, not calibrated.

Items 1 and 2 are small, and would raise held-out recall. They are left for the owner to approve as a
`rules:v2.1`, measured on a fresh independent set, not on these held-out messages, which have now been
seen.
