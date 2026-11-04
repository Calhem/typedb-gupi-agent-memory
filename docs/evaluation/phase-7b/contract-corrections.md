# Stage 2A contract corrections

**How each correction was made:**
- **Tests first:** each correction began with tests that failed. The original failures are saved in
  `stage-2a/`.
- **Changes:** the implementation changes are the smallest that make the tests pass.
- **Historical check:** after each correction, the historical results were rechecked (see the
  "Historical compatibility" section below).

## C1: one admissibility rule for schema-aware validation and the store (fixed)
**Root cause:**
- **The two encodings:** the candidate format (`gupi.candidate/1`) carries a generic statement's predicate
  and object text as `values` (`predicate-text`, `object-text`).
- **Where they were stripped:** `SchemaInfo.attributes` is built for the older Phase 2 extraction contract.
  That contract has dedicated `predicate` and `object_text` fields, so the list deliberately leaves those
  two attributes out (`CORE_CLAIM_ATTRIBUTES`).
- **The first consequence:** `validate(cset, obs, schema)` reused that list, so it rejected **every**
  statement candidate's own predicate.
- **The second consequence:** `store.submit` and `form()` validated **without** any schema by default. So the
  same candidate was formed, and so would a schema violation have been, such as an employer that is a person.

**Fix:**

| Change | Where |
|---|---|
| `SchemaInfo.owned`: every string attribute each type owns, core included (`attributes` is unchanged) | `gupi/extraction/contract.py` |
| statement values (`predicate-text`, `object-text`) are allowed only on a type that owns them; a statement needs a subject and exactly one predicate, and at most one object text; formation-set attributes (polarity, commitment, attribution-mode, …) are refused as values; `predicate-text` on a non-statement is refused | `gupi/formation/validate.py` |
| `store.submit` and `form()` validate with the live schema when the caller passes none (`form.live_schema`, read once per `Memory`) | `gupi/formation/store.py`, `form.py` |

**Before and after:**

| Case | Before | After |
|---|---|---|
| well-formed statement, schema-aware validation | rejected ("statement has no attribute 'predicate-text'") | valid |
| the same statement through `store.submit` | formed (no schema check) | formed (schema check passes) |
| employment with a person as employer, through `store.submit` | **formed** | **refused at submit** (schema) |
| statement with no predicate, two predicates, or no subject | accepted | rejected (`statement`) |
| a statement with no object ("Kim retired") | — | valid (the schema allows `object @card(0..)`) |
| `commitment` supplied as a value | accepted | rejected (`value`) |
| `rules:v2` / `rules:v2.1` candidates on the frozen 6B set, with the schema | valid | valid |

**Tests:**
- **The new ones:** `tests/integration/test_c1_schema_validation.py`, 10 tests.
- **The original failures:** `stage-2a/c1-original-failures.txt`, 8 failures before the fix.
- **One corrected test:** a test that wrongly required statements to have an object was removed before the
  fix.
- **The old expected failure:** the strict expected failure from Stage 1 (`test_contract_c1.py`) is retired.

## D3: correction-target safety
**Policy:** a correction or retraction whose target is unidentified or ambiguous requires review, and it
never changes an existing claim by itself.

**What already held, and was confirmed by tests:**
- every stated correction (a relation, or a correction cue) goes to **review**
- nothing is superseded automatically: `Memory.supersede` is the only way, and only a reviewer calls it
- the source passage and the correction text stay in the stored payload

**Defects found and fixed** (in the suggestion shown to reviewers, `form._suggest_corrections`):

| Case | Before | After |
|---|---|---|
| the extractor names one target, while other believed claims about the same proposition are plausible | `resolved` to the named one (a silent choice) | `ambiguous`, every plausible target listed |
| the named target is no longer believed (e.g. superseded) | `resolved` to it | not offered, with the reason stated |

**Scenario tests** (`tests/integration/test_d3_correction_targets.py`; 2 of the 7 failed before the fix, as
listed in `stage-2a/d3-original-failures.txt`). Every test also checks that no claim is superseded or loses
belief.

| Scenario | Result |
|---|---|
| explicitly identified target | review; suggestion `resolved` to that claim |
| no identifiable target | review; `missing`; nothing invented |
| several plausible targets | review; `ambiguous`, all listed |
| target in another conversation | review; `missing` (no cross-conversation match without identity) |
| unresolved pronoun ("Correction: She joined …") | no candidate (rules:v2.1 rejects it as an unresolved reference) |
| previously superseded target | review; not suggested as resolved |
| retraction with no identifiable target | review; `missing` |

**What the current representation cannot enforce (stopped for approval):**
- **The gap:** a correction expressed *without* a leading cue ("Sorry, I meant April") and *without* a single
  resolvable earlier candidate has no way to reach review.
- **Why:**
  - **The relation:** `relations` require a resolvable target.
  - **The cue:** the formation cue only checks the start of the passage.
  - **Inventing an id:** a placeholder id would be an invented identifier, which the policy forbids.
- **What `model:candidate-v1` does meanwhile:** it produces **no candidate** in that case (outcome
  `correction-target-unresolved`), so nothing is formed. The evidence is kept in the extractor's report.

**The minimum contract extension proposed:**
- **The version:** `gupi.candidate/1.1`, adding an optional value only.
- **What changes:** a relation of kind `corrects`, `retracts` or `updates` may have `target = null` ("stated,
  target unresolved").
  - **Validation:** it accepts this, for those kinds only.
  - **Formation:** it always routes such a candidate to review, and its suggestion is `missing` or
    `ambiguous`.
- **Compatibility:** existing candidates and their ids are unchanged, because a null target never occurs in
  version 1.
- **It needs approval.**

## Organisational claimants: investigation (C2)
| Question | Finding |
|---|---|
| A schema limitation? | **No.** `assertion:asserter` may be played by any referent (person, organisation, unclassified). |
| An identity-resolution defect? | **No, a consequence.** Referent ids include the kind, so a person "Reuters" and an organisation "Reuters" are two referents: the misclassification splits identity. |
| A candidate-contract limitation? | **Yes.** `Attribution.asserted_by` is a bare string, with no kind. |
| A persistence-mapping defect? | **Yes.** `form._claim` always creates the asserter as a **person**, and treats even a referent id (which the field's own documentation allows) as a name. |

**The four cases, as tests** (`tests/integration/test_claimant_kinds.py`):
- **Represented correctly today:**
  - **An individual claimant** ("According to Dana Okoro, …"): a person.
  - **A statement forwarded from a person:** that person is the claimant, in mode forwarded.
  - **An unknown claimant** ("Reportedly …"): no asserter is created, and no identity is invented.
- **Defined, not yet correct (strict expected failures):**
  - **An organisational claimant** ("According to Halden Press, …") should be an organisation.
  - **A claimant of unknown kind** ("According to Quill, …") should be unclassified, not a person.

**What `model:candidate-v1` does meanwhile:**
- **No person is inferred:** it never infers a person from the fact that someone makes an assertion.
- **The rule:** a claimant must be stated by the model as a person to produce a candidate. Anything else gives
  `claimant-kind-not-representable`, with no candidate.
- **The header case:** a forwarded message's header sender, whose kind the text does not state, is treated
  the same way.

**The proposed solution (needs approval):**
- **The version:** `gupi.candidate/1.1`, an optional, additive change.
- **The new field:** `Attribution.asserted_by_kind` (`person`, `organization`, `unclassified`).
  - **When it is absent,** it is left out of the candidate id, so existing ids are unchanged.
  - **Validation:** it checks the kind against the schema's referent types.
- **Persistence:** it uses the stated kind. When the kind is absent:
  - **For version 1 candidates:** it keeps today's `person`. Changing it would change the claim ids of
    historical reported claims.
  - **For version 1.1:** it uses `unclassified`.
- **What it needs:** no schema migration. This is a candidate-contract change, so it is stopped here, as
  required.

## Historical compatibility (rechecked after the last production change)
| Check | Result |
|---|---|
| D1/D2 version comparison (frozen 6B, Phase 2 conversations, 6C adversarial cases, Phase 4 world end to end, Phase 4 v1/v2 answers against the committed results, 7A probes, LoCoMo and LongMemEval candidate counts) | identical to the committed `extractor-d1-d2/comparison.json` |
| Phase 6D world, Phase 2, frozen 6B and adversarial parts | identical to `phase-6d/first-run` |
| Phase 7A probes and path comparison (both use the store) | identical to the committed results |
| historical result files, fixtures, `rules:v2`, `rules:v2.1`, the extractor registry, schema, migrations | unchanged (git) |

**Not rerun:**
- **The 6D LoCoMo and LongMemEval retrieval parts:** they form no candidates, so no store code runs. Their
  candidate counts are covered by the comparison above.
- **The Phase 6D runner itself:** it now refuses to run, correctly, because its frozen manifest records the
  old hashes of `form.py`, `store.py` and `validate.py`. Its parts were run directly instead.
- **The manifest:** it was left unchanged, as a historical record.

**Reproduction:**

    uv run pytest -q tests/integration/test_c1_schema_validation.py tests/integration/test_d3_correction_targets.py tests/integration/test_claimant_kinds.py
    uv run python -I -m gupi.benchmarks.diagnosis.versions --json /tmp/check.json   # compare with docs/evaluation/extractor-d1-d2/comparison.json
