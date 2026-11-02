# Project notes for AI coding agents

Project: **GUPI** (`typedb-noodlelab-GUPI`, Python package `noodle_memory`): a semantic memory and
context engine on TypeDB 3. Noodlelab is the owner's umbrella name for experimental projects.

## Who this is for
The owner has no programming background and is learning as we go. Explain new terms in plain English,
keep steps small, verify each step works before moving on, and stop at each phase gate for review.

## Status
Phase 0 done, awaiting review. Do not start Phase 1 until the owner approves the proposal in
docs/phase-1-plan.md. No UI, connector framework or leaderboard work before the core model is tested.

## Rules
- TypeDB 3.14.1 is the only database. No second store (vector, cache, SQL) for application data.
- Observations, facts (hypotheses until reviewed) and reviews are separate (docs/adr/0001).
  Facts are never mutated; corrections are supersessions, status changes are reviews.
- Never invent dates or treat an unknown end as "still true" (docs/adr/0003).
- An LLM output is a hypothesis, never accepted truth by default.
- Secure by default: read-only source connectors, bounded sampling, no secrets in logs or git.
- Ports: 1734 (TypeDB driver), 8005 (TypeDB HTTP/Studio), bound to 127.0.0.1.
- Python runs on the host through uv (Python 3.13).

## Checks (run before every commit)
- `docker compose up -d`, then `uv run pytest -q` (live tests skip if TypeDB is down; say so if they did).
- Tests only create and delete `gupi-test-*` / `gupi-probe-*` databases.

## Verified TypeDB 3.14.1 / typedb-driver 3.14.0 facts
- Connect: `TypeDB.driver(addr, Credentials(u, p), DriverOptions(DriverTlsConfig.disabled()))`.
- `driver.server_version()` returns an object: use `.version` ("3.14.1") and `.distribution`.
- **No native vectors**: `value vector(...)`, `@index(hnsw:...)`, list-valued attributes and
  `cosine_similarity_search` are all rejected (vectors are an unmerged PR, typedb/typedb#8014).
  Embeddings are base64 float32 strings; similarity is exact, in Python (docs/adr/0002).
- Works: abstract relation with no roles whose subtypes add roles; abstract relations playing roles;
  abstract attributes with `sub` children; `@values(...)`, `@range(0.0..1.0)`, `@card(2..2)`;
  `datetime-tz` literals like `2025-06-01T00:00:00Z`; functions taking `datetime-tz` and returning
  `{ fact }` streams; `let $f in fun(...)` in match; several relation instances with the same players.
- `alias` is a reserved keyword (cannot name a role).
- `define` of an existing function fails ("already exists"); use `redefine`. Type definitions are idempotent.
- `fetch { "x": $f.attr }` on an absent optional attribute returns null (None in Python).
- typedb-driver 3.14.0 prints a harmless SyntaxWarning on import (filtered in pytest).

## Git
- `main` holds reviewed states; work happens on `feature/<phase>-<topic>` branches.
- Conventional commits: `type(scope): imperative summary`, body says what and why, ends with the
  co-author line. No remote configured yet: ask before creating one or pushing.
