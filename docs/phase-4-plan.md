# Phase 4 plan: structured retrieval (revised after the owner's decisions)

Goal (gate, from the brief): structured retrieval, temporal filtering and multi-hop traversal; `search`,
`query`, `history`, `explore`, `explain`; answers with citations and abstention; no unsupported factual
assertions; compared against a simple text-only baseline.

## Owner decisions (2026-11-02)
Entirely offline: no credentials or paid services. Embeddings and LLM question answering deferred.
Filtering moves into TypeDB; no loading every claim and no unrestricted pairwise comparison in Python.
Multi-hop exploration and historical views. Keyword search over source text as the baseline, benchmarked
against structured retrieval on a frozen dataset. Conflicting, rejected and hypothetical claims handled
correctly. Conflict rules stay configurable; identity suggestions stay provisional. No distributed memory,
dynamic agent modes or additional databases.

## Design
1. **TypeDB-side filtering** (migration core/0007): `believed_claim($c, $t)` and `hypothesis_claim($c, $t)`
   functions take a claim and a time, so TypeDB evaluates them only for candidate claims; `believed_at` is
   redefined on top of `believed_claim` so there is one definition. Candidate claims are found by
   proposition key, role player, type and values in TypeQL; only those are fetched.
   The review queue, `ask`, identity groups and conflict detection all use these. Conflicts are compared
   only inside buckets TypeDB finds (`reduce count groupby` over proposition keys and constraint groups),
   never across all claims. Identity suggestions group referents by label in TypeDB.
2. **Spell assembly (found while writing the benchmark).** "Joined in January" and "left in May" are two
   claims; neither alone says she was there in March. When believed claims about one proposition certainly
   started by v and certainly had not ended by v, and none says FALSE at v, the answer is TRUE, labelled as
   assembled from those claims (it assumes one continuous spell). The same-spell test is corrected for
   window bounds, whose latest value is exclusive.
3. **Value-filtered questions:** for "was she CTO", claims about the same relationship without a title can
   only say FALSE (if the job had ended, so had the title), never TRUE.
4. **`query(Question)`:** a claim type, fixed roles (by referent id or by name), at most one open role
   ("who?"), optional values, a valid time and a belief time. The result has an answer per candidate and
   overall (TRUE / FALSE / UNKNOWN / NOT_YET_KNOWN / CONTESTED), citations (quote, source, said-at,
   claim, status, basis), the temporal context (times used, bounds, assumptions, assembly), what was
   excluded and why (rejected, retracted, superseded, unreviewed, not yet recorded), and the retrieval steps.
   A name that matches several referents not accepted as the same is reported as ambiguous.
5. **`explore(referent, depth)`** walks believed claims hop by hop (one TypeDB query per hop, limited
   nodes), merging accepted identities. **`history(referent)`** gives both time axes: when each claim was
   recorded and decided, and the period it claims.
6. **Keyword search:** TypeDB's case-insensitive `contains` finds candidate observations received by the
   belief time; BM25 ranks only those in Python. Behind the existing `SimilaritySearch`-style boundary.
7. **Benchmark:** a frozen world (three synthetic conversations, gold claims, review decisions) and frozen
   questions with gold answers and gold evidence, committed before the query code. Two configurations:
   claims from the gold annotations (isolates retrieval) and claims from the offline rule extractor
   (end to end). Compared with a keyword-only baseline that answers from passages. Metrics: answer
   accuracy, abstention on UNKNOWN / NOT_YET_KNOWN questions, citation precision and recall.
8. **Performance:** a deterministic synthetic memory (thousands of claims) to time `ask`, `query`, the
   review queue, conflicts and keyword search, before and after server-side filtering.
