# Phase 2 report: text memory extraction

Date: 2026-11-02. Branch: `feature/phase-2-extraction`. Server: TypeDB CE 3.14.1; typedb-driver 3.14.0;
Python 3.13; optional `anthropic` 2.4.0.

## Gate
"Ingest conversations and plain text; extract candidate entities, claims, relationships, events and
temporal expressions with uncertainty and evidence spans; test on held-out example conversations with
documented extraction errors." **Met for the offline extractor**: held-out results and the error taxonomy
are in docs/evaluation/phase-2-extraction.md. **Open for Claude**: built and tested with a simulated
client, but not run, because no Anthropic credentials exist on this machine ($0 spent).

## Owner decisions, and where each is enforced
| Decision | Enforcement | Tested in |
|---|---|---|
| Claude as provider, optional | `gupi.extraction.claude`, `claude` extra | test_claude_extractor.py |
| Offline deterministic default | `RuleExtractor`, no network | test_rules.py, test_evaluation.py |
| $10 total, fail-closed | `gupi.budget.Ledger` in its own TypeDB database | test_budget.py, test_claude_extractor.py |
| Generic claim provisional, separate | core/0003 `statement`; `ClaimView.provisional` | test_extraction_schema.py |
| Prefer typed claims | `people/predicates.json` conversion; prompt rule | test_extraction_pipeline.py |
| Original text kept; explicit vs inferred | verbatim observations, exact-span checks, `extraction-basis` | test_extraction_pipeline.py |
| No automatic acceptance | pipeline writes no reviews | test_extraction_pipeline.py, test_claude_extractor.py |
| Generic claims keep provenance, identity, time rules | referent subject, evidence, same bounds | test_extraction_schema.py |
| No autonomous schema evolution | unknown kinds -> `unclassified`; unknown types/roles/attributes rejected | test_extraction_pipeline.py |

## Tests
`uv run pytest -q`: **120 passed**, none skipped, against the live server (also passes without the optional
`anthropic` package installed). New in Phase 2: time expressions (26), rule extractor (4), extraction
schema (4), pipeline and validator (14), budget ledger (5), Claude extractor with a simulated client (6),
evaluation regression on the development set (1), Phase 1 -> 2 database upgrade (1).

## Evaluation (offline rule extractor)
Development: claims P 1.00 / R 0.92. Held-out (run once, rules frozen beforehand): claims P 1.00 / R 0.50,
all matched time bounds correct. Five held-out misses are phrasings the rules do not cover, one is a
pronoun. Details: docs/evaluation/phase-2-extraction.md.

## Decisions
ADR 0005 (new): extraction pipeline and LLM ledger. ADRs 0001-0004 unchanged.

## Limitations
- Claude extraction is untested against the real API (no credentials). The first real run may expose
  prompt or schema issues; the budget protects against cost surprises, not against poor output.
- Rule extractor recall is low on unseen phrasing; no coreference ("she", "he").
- Referents are per conversation; "Alice" in two conversations is two referents until Phase 3.
- A refused LLM extraction is recorded and not retried automatically.
- The ledger assumes one extraction process at a time (no cross-process lock).
- Evaluation sets are small and synthetic.

## Commits
`9475302` plan · `8934396` schema · `1ed46d1` time · `aa0f69a` contract/pipeline · `814f501` held-out
fixtures (before rules) · `7dcbff8` rules + evaluation · `542e42b` ledger · `eb90471` Claude extractor ·
plus this documentation commit.

## Next
Phase 3 proposal: docs/phase-3-plan.md. Running the Claude evaluation needs a key from the owner.
