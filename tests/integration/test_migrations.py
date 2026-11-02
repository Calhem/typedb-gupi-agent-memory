"""Versioned migrations, including migrating a database that already holds data, against the live server."""

import shutil

import pytest
from helpers import HR, Clock, observe, record, reports
from typedb.driver import TransactionType

from gupi import migrations, typeql
from gupi.memory import Memory
from gupi.typedb.connection import transaction

pytestmark = pytest.mark.integration

V1 = """define
  attribute note-text, value string;
  entity note, owns note-text;
"""
V2 = """define
  attribute note-status, value string;
  note owns note-status;
  fun open_notes() -> { note }:
    match $n isa note, has note-status "open";
    return { $n };
"""
V3_BACKFILL = """match $n isa note; not { $n has note-status $s; };
insert $n has note-status "open";
"""


def notes(driver, database, with_status=True):
    status = ', "status": $n.note-status' if with_status else ""
    with transaction(driver, database, TransactionType.READ) as tx:
        return sorted((d["text"], d.get("status")) for d in typeql.documents(
            tx, f'match $n isa note; fetch {{ "text": $n.note-text{status} }};'))


def test_core_packs_apply_once(driver, database):
    applied = migrations.migrate(driver, database, ["core", "people"])
    assert applied == [m.id for m in migrations.discover(["core", "people"])]
    assert applied[:3] == ["core/0001_types.schema.tql", "core/0002_functions.schema.tql",
                           "core/0003_extraction.schema.tql"] and applied[-1] == "people/0001_types.schema.tql"
    assert migrations.migrate(driver, database, ["core", "people"]) == []
    Memory.open(database, packs=("core", "people"), driver=driver)  # opening again is a no-op


def test_populated_database_migrates_with_backup_and_recovers(driver, database, tmp_path):
    pack = tmp_path / "notes"
    pack.mkdir()
    (pack / "0001_notes.schema.tql").write_text(V1)
    clock = Clock("2025-01-01")
    assert migrations.migrate(driver, database, ["notes"], extra_dirs=[pack], clock=clock) == ["notes/0001_notes.schema.tql"]
    with transaction(driver, database, TransactionType.WRITE) as tx:
        for text in ("buy milk", 'say "hi"'):
            typeql.run(tx, "insert $n isa note, has note-text == $t;", {"t": text})

    (pack / "0002_status.schema.tql").write_text(V2)
    (pack / "0003_backfill.write.tql").write_text(V3_BACKFILL)
    clock.set("2025-02-01")
    backups = tmp_path / "backups"
    applied = migrations.migrate(driver, database, ["notes"], extra_dirs=[pack], backup_dir=backups, clock=clock)
    assert applied == ["notes/0002_status.schema.tql", "notes/0003_backfill.write.tql"]
    assert notes(driver, database) == [("buy milk", "open"), ('say "hi"', "open")]
    with transaction(driver, database, TransactionType.READ) as tx:
        assert len(typeql.concept_rows(tx, "match let $n in open_notes();")) == 2

    # The pre-migration export restores the database as it was before 0002.
    schema_file = next(backups.glob("*.schema.tql"))
    data_file = next(backups.glob("*.data.typedb"))
    restored = f"{database}-restored"
    driver.databases.import_from_file(restored, schema_file.read_text(), str(data_file))
    try:
        assert notes(driver, restored, with_status=False) == [("buy milk", None), ('say "hi"', None)]
        assert "note-status" not in driver.databases.get(restored).schema()  # the pre-0002 schema came back
        assert migrations.pending(driver, restored, ["notes"], extra_dirs=[pack])[0].id == "notes/0002_status.schema.tql"
    finally:
        driver.databases.get(restored).delete()


def test_changed_or_misnumbered_migrations_are_refused(driver, database, tmp_path):
    pack = tmp_path / "notes"
    pack.mkdir()
    (pack / "0001_notes.schema.tql").write_text(V1)
    migrations.migrate(driver, database, ["notes"], extra_dirs=[pack])
    (pack / "0001_notes.schema.tql").write_text(V1 + "  attribute sneaky, value string;\n")
    with pytest.raises(migrations.MigrationError, match="changed after it was applied"):
        migrations.migrate(driver, database, ["notes"], extra_dirs=[pack])

    gappy = tmp_path / "gappy"
    gappy.mkdir()
    (gappy / "0002_late.schema.tql").write_text(V1)
    with pytest.raises(migrations.MigrationError, match="without gaps"):
        migrations.discover(["gappy"], extra_dirs=[gappy])


def test_a_failing_migration_is_not_recorded(driver, database, tmp_path):
    pack = tmp_path / "broken"
    pack.mkdir()
    (pack / "0001_bad.schema.tql").write_text("define entity oops, owns missing-attribute;")
    with pytest.raises(Exception):
        migrations.migrate(driver, database, ["broken"], extra_dirs=[pack])
    assert migrations.applied(driver, database) == {}


def test_phase_1_database_with_data_upgrades_to_phase_2(driver, database, tmp_path):
    """Build a database with the Phase 1 core (0001-0002) and data, then apply the real 0003."""
    phase1 = tmp_path / "core"
    phase1.mkdir()
    for f in sorted(migrations.BUILTIN.joinpath("core").glob("000[12]_*.tql")):
        shutil.copy(f, phase1 / f.name)
    clock = Clock("2025-01-10")
    migrations.migrate(driver, database, ["core", "people"], extra_dirs=[phase1], clock=clock)
    with pytest.raises(RuntimeError, match="needs migrating"):
        Memory(driver, database, clock)
    old = Memory(driver, database, clock, require_current_schema=False)  # stand-in for Phase 1 code
    obs = observe(HR, "hr-1", "Alice reports to Bob.", "2025-01-05")
    claim = reports(obs)
    record(old, [obs], [claim])

    clock.set("2025-02-01")
    applied = migrations.migrate(driver, database, ["core", "people"], backup_dir=tmp_path / "backups", clock=clock)
    later_core = [m.id for m in migrations.discover(["core"])][2:]  # 0003 onwards
    assert applied == later_core and applied[0] == "core/0003_extraction.schema.tql"
    new = Memory(driver, database, clock)
    new.review(claim.id, "accepted", "test")
    view = new.claim(claim.id)
    assert view.evidence[0].quote == "Alice reports to Bob." and view.basis is None
    assert new.believed_ids(clock()) == {claim.id}
    assert list((tmp_path / "backups").glob("*.data.typedb"))
