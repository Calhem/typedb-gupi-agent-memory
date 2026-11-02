# GUPI: Generalised Unitary Perceptive Integrator

A Noodlelab experiment: an open-source semantic memory and context engine for applications and AI
agents, built on TypeDB 3. GUPI stores what sources said, what was inferred from it, what was accepted,
and when each was true and when it was known, so every answer can be traced back to its evidence.

**Status: Phase 0 (feasibility).** Nothing here is usable as a product yet.

## Try the Phase 0 checks
Needs Docker and [uv](https://docs.astral.sh/uv/).

```bash
docker compose up -d          # TypeDB 3.14.1 on 127.0.0.1:1734 (Studio HTTP on 8005)
uv sync
uv run pytest -q              # unit tests + live TypeDB tests (disposable gupi-test-* databases)
uv run python -I scripts/probe_vectors.py   # which vector syntax the server accepts
```

## Layout
- `schema/core.tql`: core ontology (sources, observations, facts, evidence, reviews, time).
- `schema/functions.tql`: TypeQL functions (`believed_at`).
- `schema/domains/`: example domain schemas that extend the core.
- `src/noodle_memory/`: Python package (connection, schema loading, embeddings, valid-time logic).
- `docs/adr/`: architecture decisions.

## Licence
Apache-2.0 (to be added with the first release).
