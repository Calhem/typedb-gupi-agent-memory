# F1: forwarded copies are not new attestations

**The problem (Stage 2A finding F1, developer fixture DEV-108):**
- **What happened:** a second forwarded copy of Dana Okoro's statement was formed as a new claim.
- **The cause:** `form._existing_copies` only recognised a copy of a **first-hand** claim. When the only
  earlier claim was itself a forwarded copy, it was excluded, so every further copy looked new.
- **No format change** was needed: this is a formation fix (commit `ec6e3f5`).

**The rule now:** a forwarded or quoted candidate is withheld as a copy ("repeats existing claim …") when
memory already has a claim that matches on all of these:
- **the same type and polarity**
- **evidence with the same words** as the candidate's passage (in any conversation)
- **the origin:** either
  - the existing claim is first-hand (not forwarded or quoted), **or**
  - it is a copy of the **same original claimant**. Labels are compared word by word, and "no claimant named"
    counts as the same unknown origin, never as a new one.

**What follows from it:**
- **The earliest matching claim is the one cited.**
- **Merging:** withholding merges nothing and touches no referent.
- **Different original claimants** are never copies of each other.
- **Two people independently stating the same thing** are two attestations. So are two people *quoting* the
  same source in their own words: both reports are kept, but qualification counts **one** originator.
- **The independent count** (`qualification.independent`) counts distinct originators by asserter, so
  copies never inflate corroboration.

## Tests (`tests/integration/test_f1_forwarded.py`; before the fix, exactly the 3 copy-of-a-copy cases failed: `before/f1-original-failures.txt`)
| Required case | Test | Claims | Independent |
|---|---|---|---|
| one original | `test_one_original_assertion` | 1 | 1 |
| forwarded once | `test_the_same_assertion_forwarded_once` | 1 (copy withheld) | 1 |
| forwarded again | `test_a_forwarded_copy_forwarded_again` | 1 (second copy withheld) | 1 |
| several documents | `test_one_original_in_several_documents` | 1 (three copies withheld) | 1 |
| independent assertions | `test_two_genuinely_independent_assertions_stay_distinct` | 2 | 2 |
| two people quoting one source | `test_two_people_quoting_the_same_original_source` | 2 | 1 |
| re-ingestion | `test_repeated_ingestion_of_the_same_forwarded_document` | 1; same candidate ids; one decision | — |
| incomplete provenance | `test_forwarded_copies_with_incomplete_provenance_are_not_corroboration` | 1 | 1 |
| different originators | `test_different_original_claimants_are_not_copies` | 2 | 2 |
| a correction to a forwarded assertion | `test_a_correction_to_a_forwarded_assertion` | review; the forwarded claim is offered as the target; nothing superseded | — |

**Where it shows:** the developer fixtures.
- **DEV-108:** it is now withheld for both systems.
- **Agreement with the gold `expected_admission`:** 14/14 (`rules:v2.1`) and 18/18 (`model:candidate-v1.1`).
- **`copies_formed`:** 0.
