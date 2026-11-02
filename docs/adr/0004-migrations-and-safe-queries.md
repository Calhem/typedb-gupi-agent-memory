# ADR 0004: Schema migrations and safe query construction

Status: accepted (Phase 1), 2026-11-02

## Migrations
- Schema lives in **packs** (`src/gupi/schema/<pack>/`): `core`, example domain `people`; callers can add
  their own pack directories. Files are numbered `NNNN_name.schema.tql` (schema transaction) or
  `NNNN_name.write.tql` (write transaction, for backfills), with no gaps.
- Each applied file is recorded as a `migration` (id `pack/file`, SHA-256, applied-at) **in the same
  transaction** as the change, so a migration is applied fully or not at all.
- Applied files must never change; a checksum mismatch stops migration. Changes are new files.
- TypeDB facts this relies on (verified on 3.14.1): re-defining existing types is a no-op; re-defining an
  existing function fails, so function changes use `redefine` in a new file; schema transactions may also
  write data.
- **Recovery path** (migrations only go forward): `Memory.open(..., backup_dir=...)` exports a database
  that holds data before applying anything, with TypeDB's own `export_to_file`. To recover, import the
  export into a new database (`driver.databases.import_from_file`) and fix forward. Tested end to end
  in `tests/integration/test_migrations.py`.

## Safe queries
- Values never appear in query text. They are passed through the driver's `given_rows` and declared in a
  TypeQL `given $name: type;` stage, then used as `has attr == $name` (verified on 3.14.1).
- Only labels (type, role and attribute names) are written into query text. They must match
  `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, and claim/referent types must exist in the live schema.
- A test ingests text written to look like a TypeQL injection and checks it is stored verbatim and
  changes nothing else.

## Idempotency
Ids are derived from content (`gupi.ids`): observations from source, record key and content hash;
claims from type, players, values, bounds, evidence and method; decisions from what they decide. A batch
is one write transaction that skips ids already present, so re-ingestion and resumption after an
interrupted run create nothing twice. `@key` on `gupi-id` is TypeDB's own backstop.
