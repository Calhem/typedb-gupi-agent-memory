"""Versioned schema migrations (docs/adr/0004-migrations.md).

A pack is a directory of numbered files: `NNNN_name.schema.tql` runs in a schema transaction,
`NNNN_name.write.tql` in a write transaction (for data backfills). Packs ship in gupi/schema/<pack>/;
callers may pass extra pack directories. Each applied file is recorded in the database as a `migration`
(pack/file id + SHA-256), in the same transaction as the change, so a migration is applied fully or not at
all. Applied files must never change: a checksum mismatch stops everything.

Migrations only go forward. Recovery is: export (done automatically before migrating a database that
holds data, when a backup directory is given), fix, rebuild from the export or re-ingest.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from typedb.driver import TransactionType

from gupi import typeql
from gupi.typedb.connection import transaction

BUILTIN = Path(__file__).resolve().parent / "schema"
FILENAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.(schema|write)\.tql$")

BOOTSTRAP = """
define
  attribute migration-id, value string;
  attribute migration-checksum, value string;
  attribute migration-applied-at, value datetime-tz;
  entity migration, owns migration-id @key, owns migration-checksum, owns migration-applied-at;
"""


class MigrationError(Exception):
    pass


@dataclass(frozen=True)
class Migration:
    pack: str
    path: Path

    @property
    def id(self):
        return f"{self.pack}/{self.path.name}"

    @property
    def kind(self):
        return TransactionType.SCHEMA if self.path.name.endswith(".schema.tql") else TransactionType.WRITE

    @property
    def text(self):
        return self.path.read_text(encoding="utf-8")

    @property
    def checksum(self):
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


def discover(packs, extra_dirs=None):
    """All migrations for the named packs, in order: packs in the order given, files by number."""
    dirs = {p.name: p for p in BUILTIN.iterdir() if p.is_dir()}
    dirs.update({Path(d).name: Path(d) for d in extra_dirs or ()})
    found = []
    for pack in packs:
        if pack not in dirs:
            raise MigrationError(f"unknown schema pack: {pack}")
        files = sorted(f for f in dirs[pack].iterdir() if f.suffix == ".tql")
        numbers = []
        for f in files:
            match = FILENAME.match(f.name)
            if not match:
                raise MigrationError(f"bad migration file name: {f}")
            numbers.append(int(match.group(1)))
        if numbers != list(range(1, len(numbers) + 1)):
            raise MigrationError(f"pack {pack} must be numbered 0001, 0002, ... without gaps: {numbers}")
        found += [Migration(pack, f) for f in files]
    return found


def applied(driver, database):
    """{migration id: checksum} for everything already applied."""
    with transaction(driver, database, TransactionType.SCHEMA) as tx:
        tx.query(BOOTSTRAP).resolve()  # defining existing types again is a no-op
    with transaction(driver, database, TransactionType.READ) as tx:
        docs = typeql.documents(tx, 'match $m isa migration; fetch { "id": $m.migration-id, "sum": $m.migration-checksum };')
    return {d["id"]: d["sum"] for d in docs}


def has_data(driver, database):
    with transaction(driver, database, TransactionType.READ) as tx:
        return bool(typeql.concept_rows(tx, "match $x isa! $t; { entity $t; } or { relation $t; }; not { $x isa migration; }; limit 1;"))


def pending(driver, database, packs, extra_dirs=None):
    done = applied(driver, database)
    todo = []
    for m in discover(packs, extra_dirs):
        if m.id in done:
            if done[m.id] != m.checksum:
                raise MigrationError(f"{m.id} changed after it was applied; add a new migration instead")
        else:
            todo.append(m)
    return todo


def migrate(driver, database, packs, extra_dirs=None, backup_dir=None, clock=None):
    """Apply pending migrations in order. Returns the ids applied.

    If the database already holds data and `backup_dir` is given, it is exported there first.
    """
    clock = clock or (lambda: datetime.now(timezone.utc))
    todo = pending(driver, database, packs, extra_dirs)
    if todo and backup_dir is not None and has_data(driver, database):
        export(driver, database, backup_dir, clock())
    for m in todo:
        with transaction(driver, database, m.kind) as tx:
            tx.query(m.text).resolve()
            typeql.run(
                tx,
                "insert $m isa migration, has migration-id == $id, has migration-checksum == $sum, "
                "has migration-applied-at == $at;",
                {"id": m.id, "sum": m.checksum, "at": clock()},
            )
    return [m.id for m in todo]


def export(driver, database, backup_dir, when):
    """Export schema and data with TypeDB's own export; returns the two file paths."""
    stamp = when.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = Path(backup_dir)
    folder.mkdir(parents=True, exist_ok=True)
    schema_file = folder / f"{database}-{stamp}.schema.tql"
    data_file = folder / f"{database}-{stamp}.data.typedb"
    driver.databases.get(database).export_to_file(str(schema_file), str(data_file))
    return schema_file, data_file
