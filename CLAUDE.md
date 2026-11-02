# Project notes for AI coding agents

Project: **GUPI** (`typedb-gupi-agent-memory`, Python package `gupi`): a semantic memory and context
engine on TypeDB 3. Noodlelab is the owner's umbrella name for experimental projects.

## Who this is for
The owner has no programming background and is learning as we go. Explain new terms in plain English,
keep steps small, verify each step works before moving on, and stop at each phase gate for review.

## Status
Phase 1 done on `feature/phase-1-core`, awaiting review (docs/phase-1-report.md). Do not start Phase 2
until the owner approves docs/phase-2-plan.md. No distributed agents, packet protocols or dynamic schema
modes yet; keep the code open to them without building them.

## Rules
- TypeDB 3.14.1 is the only persistent store. No second database, vector store, cache or broker.
- Observations, claims (hypotheses until reviewed) and decisions are separate (docs/adr/0001).
  Claims are never mutated; corrections are supersessions; status changes are reviews.
- One claim per attestation; claims about the same proposition share a proposition-key.
- Never invent dates or treat an unknown end as "still true" (docs/adr/0003). Absence is never FALSE.
- Transaction times come only from GUPI's clock; callers cannot backdate them.
- Values go into queries only as `given` parameters; only validated labels go into query text (ADR 0004).
- Schema changes are new numbered migration files; never edit an applied one.
- An LLM output is a hypothesis, never accepted truth by default.
- Secure by default: read-only source connectors, bounded sampling, no secrets in logs or git.
- Ports: 1734 (TypeDB driver), 8005 (TypeDB HTTP/Studio), bound to 127.0.0.1.
- Python runs on the host through uv (Python 3.13). Machine-specific notes: CLAUDE.local.md (git-ignored).
- This repository is public: never commit secrets, local paths, backups or personal data.

## Checks (run before every commit)
- `docker compose up -d`, then `uv run pytest -q`. Live tests skip if TypeDB is down: say so if they did.
- Tests only create and delete `gupi-test-*` / `gupi-probe-*` databases.

## Verified TypeDB 3.14.1 / typedb-driver 3.14.0 facts
- Connect: `TypeDB.driver(addr, Credentials(u, p), DriverOptions(DriverTlsConfig.disabled()))`.
- `driver.server_version()` returns an object: `.version` ("3.14.1"), `.distribution`.
- Parameters: `tx.query("given $v: string, $t: datetime-tz; insert $x isa note, has text == $v;",
  given_rows=[{...}])`. A given value used with `has` needs `==`. Datetimes must be the driver's
  `Datetime` (`Datetime.fromtimestamp(secs, nanos, offset_seconds=0)`), not Python `datetime`.
- **No native vectors** (unmerged PR typedb/typedb#8014): embeddings are base64 float32 strings (ADR 0002).
- Works: abstract relations with no roles whose subtypes add roles; abstract relations playing roles;
  abstract attributes with `sub` children; `@values`, `@range(0.0..1.0)`, `@card(2..2)`;
  `datetime-tz` literals like `2025-06-01T00:00:00Z`; functions over `datetime-tz` returning streams;
  `let $c in fun(...)`; several relation instances with the same players; data writes inside schema
  transactions; role variables (`$c links ($role: $x)`); nested fetch subqueries and `{ $c.* }`;
  `database.export_to_file` / `databases.import_from_file`; kind statements `entity $t;` / `relation $t;`.
- `alias` and `entity` are reserved (no role named `alias`; `$t sub entity` is an error: use `entity $t`).
- `define` of an existing function fails ("already exists"): use `redefine`. Type definitions are idempotent.
- Fetching an attribute type that is not in the schema is an error, not null; an absent optional
  attribute on an existing type fetches as null.
- typedb-driver 3.14.0 prints a harmless SyntaxWarning on import (filtered in pytest).

## Git
- `main` holds reviewed states; work happens on `feature/<phase>-<topic>` branches, merged after review.
- Conventional commits: `type(scope): imperative summary`, body says what and why, ends with the
  co-author line. Push each completed, passing step; confirm with `git ls-remote origin`.
