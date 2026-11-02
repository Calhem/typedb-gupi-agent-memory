"""Loading the GUPI schema into an empty database (Phase 0: no migrations yet)."""

from pathlib import Path

from typedb.driver import TransactionType

from noodle_memory.typedb.connection import transaction

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schema"


def load(driver, database, domains=()):
    """Define core types, then each named domain (schema/domains/<name>.tql), then functions.

    Functions are not idempotent under `define` (a second define fails), so this is for fresh databases only.
    """
    files = [SCHEMA_DIR / "core.tql"] + [SCHEMA_DIR / "domains" / f"{d}.tql" for d in domains]
    files.append(SCHEMA_DIR / "functions.tql")
    with transaction(driver, database, TransactionType.SCHEMA) as tx:
        for path in files:
            tx.query(path.read_text()).resolve()
