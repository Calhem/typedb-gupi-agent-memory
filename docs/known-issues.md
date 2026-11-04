# Known issues and open considerations

Items the owner has asked to keep visible until they are resolved. Last updated 2026-11-03.

## Unresolved compliance consideration: LoCoMo licence
- **What:** LoCoMo (snap-research/locomo, commit `cbfbc1d…`) is licensed **CC BY-NC 4.0**: use is allowed
  for non-commercial purposes with attribution; no redistribution of the content here.
- **Current handling:** used only for offline research evaluation of an open-source experiment; the data is
  kept outside the repository (`.data/`, git-ignored); only ids, checksums, configuration and aggregate
  metrics are committed (checked before the Phase 5 merge: 0 of 300 sampled dataset passages found in
  tracked files).
- **Open question:** whether the project's context (developed by an employee of a company) counts as
  non-commercial use has **not been reviewed**. Until it is, LoCoMo results must not be used in commercial
  material, product claims or marketing, and LoCoMo must not become a dependency of any product.
- **Also non-commercial:** AVeriTeC (CC BY-NC 4.0) was assessed but not downloaded.
- **Owner:** project owner; resolve before any external or commercial use of LoCoMo-derived results.

## Known limitation: vector-search performance
- Embeddings are stored in TypeDB as base64 float32 strings (TypeDB 3.14.1 has no vector type; ADR 0002,
  0008) and searched exactly in Python after reading them from TypeDB.
- Measured (docs/evaluation/phase-5/embeddings.json, one laptop): reading 50,000 vectors takes 4.8 s and
  exact cosine 0.5 s (NumPy) or 1.6 s (pure Python); cost grows linearly with the number of vectors in scope.
  Writing runs at about 290 vectors/s. Generating embeddings locally is slower still: 8.6 long texts/s
  (about an hour for 32,000 LongMemEval turns).
- **Fine for** per-question or per-conversation scopes (hundreds to a few thousand vectors).
  **Not suitable for** whole-memory similarity search at scale.
- **Planned remedy:** a TypeDB-native vector index once a released TypeDB version supports it (canary test
  in tests/integration/test_smoke.py), behind the existing `SimilaritySearch` interface; until then, narrow
  the scope first (contexts, time windows) before searching.

## Known limitation: "since <date>" read as an exact start date
- **What:** phrases such as "Since March 2025, Nora Vance works at Halden as CTO" are turned into a claim
  whose **start** lies in March 2025. Both the offline rule extractor and the frozen Phase 4 gold claims do
  this.
- **The other reading:** such phrases are often only **lower-bound evidence of continuity**: "it has held
  at least since March". They do not say it began then.
- **Effect:**
  - Under answer semantics v2, the March "start" can compete with an earlier stated start (Q9). This is why
    Phase 4 question q01 is UNKNOWN under v2 (docs/evaluation/phase-4-v2.md).
  - Read as lower-bound evidence, it would not compete, and q01 would be PRESUMED.
- **Handling:** address it in Memory Formation Engine development: how such phrases become claims, and a way
  to record "held at least since" without a start. **Do not** change the frozen Phase 4 benchmark, its gold
  claims or its scoring to fix it.
- **Owner:** project owner; to be picked up when the Memory Formation Engine starts.

## Known limitations: memory formation and the candidate store (Phase 6)
These are recorded at the Phase 6 merge (docs/formation/candidate-store.md). None changes how GUPI answers
existing data. They matter when formation is used.

- **S7, unauthenticated reviewer identities.** A reviewer is a plain string passed by the caller. Nothing
  checks who approved or rejected a candidate, so an approval proves only what the caller claimed. Do not
  treat a recorded reviewer as an authenticated identity.
- **S8, name-based entity conflation within one conversation.** Participants are referents scoped to their
  conversation or document. Two different people with the same name in the same conversation become one
  referent, and their claims are merged. Across conversations and sources, nothing is merged (only explicit
  identity decisions merge). Fixing this needs identity resolution, which is out of scope.
- **S1, malformed candidates are not stored.** `store.submit` reports structurally invalid candidates, but
  does not keep them, so extractor errors are not durable.
- **S2, suggestions can go stale.** Correction suggestions reflect memory at the moment each decision was
  recorded. A claim added later is not reflected until the candidate is decided again.
- **S3, correction targets are found within one conversation only.** They are found by proposition key, so a
  correction of a claim from another conversation is recorded as `missing`.
- **S4, `pending` reads every stored candidate.** It is linear in the size of the store, which is acceptable
  for a prototype.
- **S5, a formed candidate's status stays `formed`** even if its claim is later retracted. The claim's own
  reviews carry the retraction.
- **S6, two formation pathways.** The candidate store is preferred for new deployments, and `form()` is
  legacy. Using both on the same candidates is refused, in either order.
- **Also:**
  - **v1 answers are not qualified.** Only v2 carries the evidential qualification.
  - **The asserter is always created as a person.**
  - **`rules:v2`'s narrow coverage** is documented in docs/formation/rules-v2.md and
    docs/evaluation/phase-6b-extraction.md.


## Unresolved evaluation disagreements: Phase 4 questions q01 and q03
Recorded 2026-11-04 (Phase 6D; docs/evaluation/phase-6d/failure-attribution.md). Neither is a proven gold
error, and the frozen gold and scorer are unchanged, so both count as misses.

| Question | Frozen gold | v2 answer | The disagreement |
|---|---|---|---|
| q01 | TRUE | PRESUMED end to end (UNKNOWN on gold claims) | the gold counts a period joined from a start and a later end as TRUE; v2 deliberately calls it PRESUMED |
| q03 | FALSE | UNKNOWN | the gold treats a later start as evidence of falsity earlier; v2 does not (ADR 0009, Q1) |

**To resolve them:** an adjudication by someone independent of GUPI. Until then, report them as open.
