# C2: claimant classification

**The problem (diagnosed in Stage 2A):**
- **The format:** `gupi.candidate/1` had no way to say what kind of thing a claimant is.
- **The storage:** `form._claim` then stored every claimant as a **person**. "Halden Press announced…" made
  Halden Press a person.
- **The schema was fine:** it already has `person`, `organization` and `unclassified` referents, and any
  referent can be an asserter.

**The fix (commit `e012f48`, format in candidate-format-1.1.md):**
- **The new field:** a candidate in format 1.1 may state `attribution.asserted_by_kind`: `person`,
  `organisation` or `unknown`.
- **Storage:** `person` → `person`, `organisation` → `organization`, and `unknown` or absent →
  `unclassified`.
- **Absence is not evidence:** a claimant with no stated kind (every 1.0 candidate, and therefore everything
  `rules:v2` and `rules:v2.1` produce) is stored as `unclassified`, never as a person.
- **No schema change.**

**Identity is kept separate from kind:**
- **The referent id:** it is computed from (conversation, kind, surface).
  - **So:** a person and an organisation with the same name are two referents. An `unclassified` "Mara Quist"
    and a person "Mara Quist" are two referents too.
- **Merging:** nothing is merged automatically. Identity groups remain reviewer decisions, as before.
- **Intermediaries:** the forwarder, or a news outlet passing on a person's words, stays in `via`. It is
  not made an asserter, and no referent is invented for it.

## Tests (`tests/integration/test_c2_claimants.py`; before the fix, 7 of 12 failed: `before/c2-original-failures.txt`)
| Required case | Test | Result |
|---|---|---|
| an individual | `test_a_named_individual` | asserter is a person |
| an organisation | `test_an_organisation_issuing_a_statement` | asserter is an organization; never also a person |
| a news organisation reporting a person | `test_a_news_organisation_reporting_a_persons_assertion` | asserter is the person; the outlet stays in `via`, no referent invented for it |
| a person forwarding an organisational statement | `test_a_person_forwarding_an_organisational_statement` | asserter is the organisation, not the forwarder |
| an organisation forwarding an organisation | `test_an_organisation_forwarding_another_organisations_statement` | asserter is the original organisation; the forwarder keeps its own kind |
| an unidentified claimant | `test_an_unidentified_claimant_creates_no_asserter` | no asserter at all |
| unknown kind | `test_an_unknown_kind_stays_unknown` | `unclassified` |
| two same-named people | `test_same_named_people_in_different_conversations_are_distinct` | two referents |
| two same-named people, one conversation | `test_same_named_people_in_one_conversation_are_not_merged` | **expected failure (S8)**, see below |
| a person and an organisation with the same name | `test_a_person_and_an_organisation_with_the_same_name_stay_distinct` | two referents, two kinds |
| legacy 1.0, no kind | `test_a_legacy_1_0_claimant_without_a_kind_is_not_made_a_person` | `unclassified`, not a person |
| identity not merged by kind | `test_claimant_identity_and_kind_are_not_merged_without_review` | two referents; no identity group formed |

**The one expected failure (S8, strict):**
- **The case:** two people with the same name in **one** conversation, where nothing in the text tells them
  apart.
- **What happens:** they get one referent id.
- **Why it is left:** that is the existing scoping rule for all referents (not just claimants). Telling them
  apart needs evidence the candidate does not carry, so changing it would be a redesign. It is recorded in
  remaining-limitations.md.

## The deliberate behaviour change
- **What changed:** claims formed **from now on** from `rules:v2` / `rules:v2.1` reported speech ("According
  to Dana Okoro, …") have an `unclassified` asserter instead of a person.
- **What did not change:**
  - already-persisted claims
  - candidate ids
  - which candidates are formed, withheld or reviewed
  - answers, qualification and the independent-originator count. These use the asserter's id, which is still
    one per claimant per conversation.
- **Where it shows:**
  - **Phase 6D:** the run against manifest v3 is identical to the first run (compatibility-results.md). Its
    results record answers, outcomes and counts, not asserter kinds, so the change itself is not visible
    there. What the run shows is that nothing it measures moved.
  - **The tests:** the change itself is shown by `test_a_legacy_1_0_claimant_without_a_kind_is_not_made_a_person`.
