# GUPI: Generalised Unitary Perceptive Integrator

An experimental, open-source semantic memory and context engine for applications and AI agents, built
on [TypeDB](https://typedb.com) 3. GUPI records what sources said, the claims drawn from them, which claims
were accepted, when each was true and when GUPI knew it, so every answer can be traced to its evidence.

**Status (2026-11-09): research paused.** GUPI's evidence model holds in tests. But it hasn't been shown to improve an agent's answers, or that TypeDB adds a measurable advantage on conversational data. The final answer-level evaluation was not run, because no independent question pack exists. Read [docs/final-report.md](docs/final-report.md) first. Research branches are kept unmerged, and `main` holds the Stage 4 state.

| Topic | Where |
|---|---|
| Final report: what was built, what works, what doesn't, TypeDB's contribution, recommendation | [docs/final-report.md](docs/final-report.md) |
| Why the final evaluation could not run | [docs/evaluation/final/pack-audit.md](docs/evaluation/final/pack-audit.md) |
| Phase reports | `docs/phase-*-report.md`, `docs/evaluation/phase-*/README.md` |
| Known issues and limits | [docs/known-issues.md](docs/known-issues.md), and section C of the final report |

## What works today
- A core ontology in TypeDB: sources, verbatim observations, typed claims (one per attestation), evidence
  spans, and reviews, corrections and alternative readings as historical events.
- Bitemporal questions: "what do we believe now about August?" vs "what did we believe in March?",
  with answers TRUE, FALSE, UNKNOWN, NOT_YET_KNOWN or CONTESTED, never guessing missing dates.
- Idempotent, all-or-nothing ingestion; versioned schema migrations with automatic backup.
- Every value is passed to TypeDB as a query parameter, never pasted into query text.
- Extraction from conversations and text into hypotheses with exact evidence spans: an offline rule-based
  extractor by default, and an optional Claude extractor behind a fail-closed spending ledger.
- Review: a queue of hypotheses, conflict detection (contradictions vs differing evidence), suggested
  identities that merge only once accepted, and corrections that can be withdrawn, via the `gupi` CLI.
- Optional local embeddings (`uv sync --extra embeddings`; BAAI/bge-small-en-v1.5 on the CPU) stored in
  TypeDB, and keyword / embedding / structured / hybrid evidence retrieval, evaluated offline on LoCoMo and
  LongMemEval (retrieval only, not official scores; datasets are not included: see docs/datasets.md).
- Structured retrieval: questions with an open role ("who was the CTO in March?") answered as of any
  belief time, with citations, the claims excluded and why, and explicit unknowns; multi-hop exploration;
  history on both time axes; keyword search over source text as the baseline. Filtering runs in TypeDB.

## Try it
Needs Docker and [uv](https://docs.astral.sh/uv/).

```bash
docker compose up -d                          # TypeDB 3.14.1 on 127.0.0.1:1734 (HTTP on 8005)
uv sync
uv run pytest -q                              # unit tests + live tests on disposable gupi-test-* databases
uv run python -I examples/quickstart.py       # the late-correction example
uv run python -I -m gupi.evaluation --set dev # offline extraction evaluation
```

Review from the command line (the database defaults to `$GUPI_DATABASE`):

```bash
uv run gupi --database demo ingest tests/fixtures/conversations/dev/d2-correction.json --create
uv run gupi --database demo queue
uv run gupi --database demo accept <claim-id> --by your-name --reason "checked"
uv run gupi --database demo conflicts
```

Structured questions from Python:

```python
from datetime import datetime, timezone
from gupi.memory import Memory

memory = Memory.open("demo", packs=("core", "people"))
result = memory.query_by_name("reporting", {"report": "Marco Rossi", "manager": None},
                              valid_at=datetime(2025, 3, 1, tzinfo=timezone.utc))
print(result.answer, result.binding, [c.quote for c in result.citations], result.excluded)
```

Benchmarks (offline): `uv run python -I -m gupi.retrieval_eval` (structured vs keyword retrieval) and
`uv run python -I scripts/benchmark_performance.py` (latency and throughput).

Claude extraction is optional: `uv sync --extra claude`, provide `ANTHROPIC_API_KEY` (or an `ant auth login`
profile), then `--extractor claude`. Every call is reserved against a spending limit before it is sent.

The default TypeDB credentials are the Community Edition defaults for a local, development-only server.
Set `GUPI_TYPEDB_ADDRESS`, `GUPI_TYPEDB_USERNAME` and `GUPI_TYPEDB_PASSWORD` for anything else.

## Layout
- `src/gupi/schema/<pack>/`: numbered schema migrations (`core`, example domain `people`).
- `src/gupi/memory.py`: ingestion, decisions, retrieval (`Memory`).
- `src/gupi/extraction/`: contract and validator, pipeline, rule and Claude extractors; `budget.py`: LLM ledger;
  `timeexpr.py`: time phrases; `evaluation.py`: extraction evaluation.
- `src/gupi/records.py`, `ids.py`, `typeql.py`, `status.py`, `temporal.py`, `retrieval.py`,
  `migrations.py`, `embedding.py`.
- `docs/adr/`: architecture decisions. `tests/unit`, `tests/integration` (live TypeDB).

## Known issues
See [docs/known-issues.md](docs/known-issues.md): LoCoMo's non-commercial licence is an unresolved
compliance consideration, and vector search is exact and linear in the number of vectors.

**Known limitations from the research** ([final report](docs/final-report.md), section C):
- Claims add no measurable recall on real chat, and few of them link two named things.
- Several temporal readings are fragile: "since" read as a start; an undated start then an end stays unknown; activities closed by past-tense mentions.
- Activity consolidation is not implemented, and final states are not reliable.
- Every favourable answer-level result comes from developer-written material.

**Reproducing the research:** the commands are at the end of the final report and in each phase's README. Datasets go in git-ignored `.data/`. Recorded model responses and annotations are private, so the phases that depend on them can't be rerun from this repository alone.

## Licence
Apache-2.0: see [LICENSE](LICENSE). GUPI is an independent Noodlelab experiment.
