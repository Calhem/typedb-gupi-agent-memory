# Phase 2 plan: text memory extraction (revised after the owner's decisions)

Goal (gate): ingest conversations and plain text, extract candidate referents, claims, events and time
expressions as **hypotheses** with evidence spans and uncertainty, and measure the errors on held-out
example conversations.

## Owner decisions (2026-11-02)
- LLM provider: Anthropic Claude. Default operation: offline, deterministic, no API calls.
- Real-extraction budget: **$10 total**, enforced by an explicit usage and cost tracker that fails closed.
- Generic claim type approved, **provisional** and separate from typed domain claims; typed claims are
  preferred whenever the schema supports them.
- Original text preserved; explicit statements distinguished from model inferences.
- Extracted claims are never accepted automatically.
- Generic claims may not bypass provenance, identity or temporal requirements.
- No broad autonomous schema evolution.

## Changes from the first draft, and why
1. **Offline default is a real extractor, not just canned output.** A deterministic, rule-based
   `RuleExtractor` (patterns for reporting lines, joining/leaving, roles, with time phrases) is the default.
   It gives a genuine offline baseline to evaluate. Canned `FixtureExtractor` output stays for tests.
2. **Claude extractor is optional.** `anthropic` becomes an optional extra (`gupi[claude]`), so the core
   stays dependency-light. Model `claude-opus-5-5` (the current default), JSON-schema structured output,
   refusals handled, and server-side refusal fallbacks enabled (`fallbacks: "default"`), with cost charged
   at the price of whichever model actually served each attempt.
3. **The budget ledger lives in TypeDB** (the only database), in a dedicated ledger database shared by all
   runs, so creating a new memory database cannot reset the $10. Before every call GUPI commits a
   *reservation* for the worst case (input bounded by its UTF-8 byte length, plus `max_tokens` output, at
   the highest price any model in the fallback chain could charge, for up to two attempts). After the call
   it records the actual usage. It fails closed: no call is made if the ledger is unreachable, a price is
   unknown, or the reservation would exceed what is left. A call whose usage cannot be read keeps its full
   reservation as spent.
4. **No credentials exist on this machine** (checked: no API key, no CLI login). The Claude path is built
   and tested against a simulated client; real runs, and the Claude half of the evaluation, wait until the
   owner supplies a key. $0 is spent until then.
5. **Generic `statement` claim** (core migration 0003): subject role players must be referents (identity
   requirement), evidence is required (provenance), and the same valid-time bounds apply (temporal
   requirement). It carries a predicate phrase and an optional literal object text, is marked provisional,
   and goes through the same review process as every other claim. A
   **prefer-typed** step converts a generic statement to a typed claim when the domain pack declares a
   mapping for its predicate (e.g. "reports to" -> `reporting`); the extractor is also told to use typed
   claims first.
6. **`extraction-basis`** on every extracted claim: `explicit` (the quoted span states it) or `inferred`
   (the model concluded it). Quotes must match the source text exactly or the item is rejected.
7. **Referents are scoped to one conversation or document.** "Alice" in two conversations gives two
   referents; merging them is Phase 3 (precision over automatic merging). Mentions and `reference`
   relations record which text span named which referent. Entities whose kind is unclear use a fixed core
   type `unclassified` instead of new schema.
8. **No schema evolution:** extraction may only use claim types, roles and attributes that already exist.
   Anything else is rejected and logged in the extraction run, never added to the schema.

## Steps (each tested, committed and pushed on `feature/phase-2-extraction`)
1. Migration core/0003: `statement`, `unclassified`, `extraction-basis`, extraction-run and LLM-call
   ledger types. Contexts and mentions in `Batch` and ingestion.
2. Deterministic time-expression normaliser (relative to observed-at; unparseable -> unknown).
3. Extraction contract, validator, prefer-typed mapping, pipeline (`FixtureExtractor` tests).
4. `RuleExtractor` (offline default).
5. Usage and cost tracker with fail-closed limit; `ClaudeExtractor` (simulated-client tests).
6. Annotated conversation fixtures (development and held-out), evaluation runner, error taxonomy and
   report. The rules are written against the development set only; held-out results are reported once,
   without tuning afterwards.

Out of scope: retrieval and answer generation (Phase 4), conflict policy and identity merging (Phase 3),
benchmarks (Phase 5), connectors other than text and conversations, schema evolution.
