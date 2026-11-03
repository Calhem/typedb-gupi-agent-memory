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
