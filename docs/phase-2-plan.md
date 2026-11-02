# Phase 2 proposal: text memory extraction

Goal (gate): ingest conversations and plain text, extract candidate referents, claims, events and time
expressions as **hypotheses** with evidence spans and uncertainty, and measure the errors on held-out
example conversations.

Small steps, each tested and committed on `feature/phase-2-extraction`:

1. **Conversation and text records.** Conversation messages become observations (record key = message id,
   observed-at = message time) inside a `context`; plain text splits into stable, offset-addressed chunks.
   Idempotent like Phase 1.
2. **Provider interface.** `Extractor` protocol: text + schema description -> structured JSON. Ships with
   a deterministic `FixtureExtractor` (canned outputs, for tests and offline runs). A real LLM provider is
   optional, behind a configuration flag, with a hard limit on calls and tokens per run.
3. **Extraction contract.** A strict JSON shape (mentions, claims with role -> mention, values, quoted time
   expressions). The validator rejects unknown types/roles, spans whose text does not match the quote,
   and dates that are not grounded in quoted text.
4. **Time normalisation.** Deterministic, rule-based: "in June" + observed-at -> a month window; "since
   2023" -> a year window plus ongoing-at-observation; "last week" -> a window relative to observed-at.
   Unparseable expressions are kept as text with UNKNOWN bounds, never guessed.
5. **Mentions and local references.** Mentions and `reference` relations within one conversation;
   ambiguous references become `alternatives`. Cross-source identity merging waits for Phase 3.
6. **Provenance of extraction.** Each claim's `method` names extractor, model and prompt version; an
   `extraction-run` record in TypeDB keeps the prompt hash, limits, token counts and timing.
7. **Evaluation.** Hand-annotated fixture conversations (changing jobs, late corrections, contradictions,
   ambiguous names), split into development and held-out sets. Report precision/recall for referents,
   claims and time bounds, and an error taxonomy.

Out of scope: retrieval and answer generation (Phase 4), conflict policy and identity merging (Phase 3),
benchmarks (Phase 5), connectors other than text and conversations.

Decisions needed from the owner:
- **LLM provider for real (non-fixture) runs**, and a spending limit. The default path needs no API key.
- **Generic carrier claims**: should the core ship a generic `property` claim (subject + named value) so
  extraction can record attribute facts without a domain schema, or should extraction only produce
  claim types that a domain pack defines? (Recommendation: domain types only, plus a small generic
  `statement` claim kept clearly separate, to avoid untyped triples.)
