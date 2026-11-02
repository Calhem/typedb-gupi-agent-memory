# Phase 4 proposal: retrieval and the answer API

Goal (gate, from the brief): structured TypeQL retrieval, temporal filtering, multi-hop traversal and
vector retrieval, combined only where useful; `search`, `query`, `history`, `explore`, `explain`; answers
with citations and abstention; no unsupported factual assertions; compared against a simple text-only
baseline.

Proposed steps:
1. **Server-side narrowing.** Move the certain TRUE/FALSE valid-time cases and status filtering into TypeQL
   functions so retrieval does not read every claim into Python (the main Phase 3 scaling limit).
2. **Structured retrieval API:** `explore(referent)` (claims, neighbours, identities), `history(referent)`
   (both time axes), multi-hop traversal over typed relations with a depth limit, all at a chosen belief
   time and valid time.
3. **Evidence search:** a deterministic lexical baseline over observation text stored in TypeDB (BM25 in
   Python, no new store), behind the existing `SimilaritySearch` interface so embeddings can be swapped in.
4. **`query(question)` and `explain(answer)`:** a structured question form first (type, roles, time) with
   answers built from claims: TRUE/FALSE/UNKNOWN/NOT_YET_KNOWN/CONTESTED, each with citations (quote,
   source, observed-at), the belief time and temporal assumptions used, and the retrieval steps.
   Abstain when only hypotheses or nothing support an answer.
5. **Optional natural-language layer:** Claude turns a question into the structured form and phrases the
   answer from retrieved evidence only, with citations checked against the evidence. Budgeted through
   the existing ledger; offline mode keeps the structured form.
6. **Evaluation:** question fixtures over the Phase 2/3 conversations with gold answers, comparing the
   structured answers with a text-only baseline (lexical search + quoting), reporting accuracy and abstention.

Decisions needed from the owner:
- **Embeddings:** stay lexical-only for Phase 4, or choose an embedding source. Anthropic does not offer an
  embeddings endpoint; options are a local model (a large new dependency, e.g. sentence-transformers) or a
  separate paid provider. Recommendation: lexical baseline now, embeddings later behind the interface.
- **Natural-language questions:** build step 5 now (needs credentials to test for real), or keep Phase 4
  structured-only and offline.
