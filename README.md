# GUPI: Generalised Unitary Perceptive Integrator

An experimental, open-source semantic memory and context engine for applications and AI agents, built
on [TypeDB](https://typedb.com) 3. GUPI records what sources said, the claims drawn from them, which claims
were accepted, when each was true and when GUPI knew it, so every answer can be traced to its evidence.

**Status: Phase 1 (core model and persistence) under review.** Not yet a product: no text extraction,
search or connectors yet. See [docs/phase-1-report.md](docs/phase-1-report.md).

## What works today
- A core ontology in TypeDB: sources, verbatim observations, typed claims (one per attestation), evidence
  spans, and reviews, corrections and alternative readings as historical events.
- Bitemporal questions: "what do we believe now about August?" vs "what did we believe in March?",
  with answers TRUE, FALSE, UNKNOWN, NOT_YET_KNOWN or CONTESTED, never guessing missing dates.
- Idempotent, all-or-nothing ingestion; versioned schema migrations with automatic backup.
- Every value is passed to TypeDB as a query parameter, never pasted into query text.

## Try it
Needs Docker and [uv](https://docs.astral.sh/uv/).

```bash
docker compose up -d                          # TypeDB 3.14.1 on 127.0.0.1:1734 (HTTP on 8005)
uv sync
uv run pytest -q                              # unit tests + live tests on disposable gupi-test-* databases
uv run python -I examples/quickstart.py       # the late-correction example
```

The default TypeDB credentials are the Community Edition defaults for a local, development-only server.
Set `GUPI_TYPEDB_ADDRESS`, `GUPI_TYPEDB_USERNAME` and `GUPI_TYPEDB_PASSWORD` for anything else.

## Layout
- `src/gupi/schema/<pack>/`: numbered schema migrations (`core`, example domain `people`).
- `src/gupi/memory.py`: ingestion, decisions, retrieval (`Memory`).
- `src/gupi/records.py`, `ids.py`, `typeql.py`, `status.py`, `temporal.py`, `retrieval.py`,
  `migrations.py`, `embedding.py`.
- `docs/adr/`: architecture decisions. `tests/unit`, `tests/integration` (live TypeDB).

## Licence
Apache-2.0: see [LICENSE](LICENSE). GUPI is an independent Noodlelab experiment.
