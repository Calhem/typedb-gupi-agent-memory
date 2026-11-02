# ADR 0005: Extraction pipeline and the LLM spending ledger

Status: accepted (Phase 2), 2026-11-02

## Extraction
- **Extractors propose; the validator decides what is recorded.** Every extractor returns the same JSON
  contract (`gupi.extraction.contract`). The validator rejects (with a reason) any mention or quote that
  does not occur exactly in the source, any claim type, role, player kind or attribute not already in
  the schema, `identity` claims (Phase 3), and malformed basis/confidence values.
- **Dates are never taken from an extractor.** Extractors return time *phrases*; a phrase must occur in
  the source text and is read by the deterministic `gupi.timeexpr`. Unreadable or ungrounded phrases leave
  the bound unknown and are noted.
- **Explicit vs inferred:** every extracted claim has `extraction-basis`. The offline extractor only
  produces `explicit`; an LLM may mark a claim `inferred` (e.g. pronoun resolution).
- **No automatic acceptance:** extraction never writes a review. Everything extracted is a hypothesis.
- **Generic claims are provisional and guarded.** `statement` needs a referent subject (identity),
  evidence (provenance) and uses the same valid-time bounds. A domain pack's `predicates.json` maps
  predicates to typed claims, and the validator converts matching statements ("prefer typed").
- **No schema evolution:** an unknown entity kind becomes the fixed `unclassified` type; anything else
  outside the schema is rejected.
- **Referents are scoped** to the conversation or document (`containment` context); merging across
  scopes is Phase 3.
- **Idempotent:** one `extraction-run` per (extractor, prompt version, observation), linked to its outputs
  and carrying a JSON report (counts, rejections, notes). A rerun skips extracted observations, so it
  never pays for the same LLM call twice. A run that hit a refusal is recorded and also not retried
  automatically; a run that failed with an error is not recorded and is retried.

## Offline default
`RuleExtractor` (deterministic patterns for the `people` domain) is the default. It makes no API calls.

## Claude
Optional (`uv sync --extra claude`). Model `claude-opus-5-5`, effort `medium`, `max_tokens` 8000 (thinking
included; it cannot be disabled on this model), JSON-schema structured output, server-side refusal
fallbacks (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`). Refusal, truncation and
unparseable output produce no claims.

## Spending ledger (fail closed)
- A TypeDB database of its own (`gupi-ledger`), shared by all runs; the limit ($10, owner decision) is
  stored there and is only changed explicitly.
- Before each request: reserve the worst case (input bounded by UTF-8 bytes + 1000; output = max_tokens;
  requested model's price plus one fallback attempt at the highest known price). Refuse if spent + reserve
  exceeds the limit or the per-run cap.
- After: charge each attempt in `usage.iterations` at its own model's price (a missing model is charged at
  the highest price). Missing token counts or any exception keep the whole reservation as spent. Only a
  request that provably never left is released.
- Prices are a table in `gupi.budget` (dated); a model not in it cannot be called.
- Known limitation: two processes reserving at the same instant could both pass the check (snapshot
  isolation). GUPI runs one extraction process at a time; a lock or serialised reservations would be
  needed before running in parallel.
