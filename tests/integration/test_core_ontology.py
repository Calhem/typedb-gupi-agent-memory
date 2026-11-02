"""The brief's bitemporal example on the draft core ontology, against the live server.

Alice's manager is recorded in January 2025 as Bob ("since March 2024, still the case").
A source received in November 2025 corrects it: Alice stopped reporting to Bob in June 2025.
What we NOW believe about August 2025 differs from what we believed in March 2025 about August 2025.
"""

from datetime import datetime, timezone

import pytest
from typedb.driver import TransactionType

from noodle_memory.temporal import Truth, ValidTime, holds_at
from noodle_memory.typedb import schema
from noodle_memory.typedb.connection import rows, transaction

pytestmark = pytest.mark.integration

DATA = """
insert
  $src isa source, has gupi-id "src:hr-notes", has source-kind "text";
  $alice isa person, has gupi-id "p:alice", has label "Alice";
  $bob isa person, has gupi-id "p:bob", has label "Bob";

  $o1 isa observation, has gupi-id "obs:1", has content "Alice has reported to Bob since March 2024.",
    has observed-at 2025-01-10T09:00:00Z, has received-at 2025-01-10T09:05:00Z;
  sourcing (source: $src, observed: $o1);
  $r1 isa reporting (report: $alice, manager: $bob), has gupi-id "fact:r1",
    has recorded-at 2025-01-10T09:05:00Z,
    has valid-from-earliest 2024-03-01T00:00:00Z, has valid-from-latest 2024-04-01T00:00:00Z,
    has valid-to-earliest 2025-01-10T09:00:00Z,
    has time-precision "month", has valid-to-basis "ongoing-at-observation";
  evidence (supported: $r1, support: $o1), has span-start 0, has span-end 43;
  review (reviewed: $r1), has verdict "accepted", has recorded-at 2025-01-10T09:05:00Z, has decided-by "fixture";

  $o2 isa observation, has gupi-id "obs:2", has content "Alice stopped reporting to Bob in June.",
    has observed-at 2025-11-14T16:00:00Z, has received-at 2025-11-15T08:00:00Z;
  sourcing (source: $src, observed: $o2);
  $r2 isa reporting (report: $alice, manager: $bob), has gupi-id "fact:r2",
    has recorded-at 2025-11-15T08:00:00Z,
    has valid-from-earliest 2024-03-01T00:00:00Z, has valid-from-latest 2024-04-01T00:00:00Z,
    has valid-to-earliest 2025-06-01T00:00:00Z, has valid-to-latest 2025-07-01T00:00:00Z,
    has time-precision "month", has valid-to-basis "stated";
  evidence (supported: $r2, support: $o1);
  evidence (supported: $r2, support: $o2), has span-start 0, has span-end 39;
  review (reviewed: $r2), has verdict "accepted", has recorded-at 2025-11-15T08:00:00Z, has decided-by "fixture";
  supersession (superseded: $r1, replacement: $r2), has recorded-at 2025-11-15T08:00:00Z, has reason "late correction";
"""

BOUNDS = ["valid-from-earliest", "valid-from-latest", "valid-to-earliest", "valid-to-latest"]


def utc(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


@pytest.fixture
def memory(driver, database):
    schema.load(driver, database, domains=["people"])
    with transaction(driver, database, TransactionType.WRITE) as tx:
        tx.query(DATA).resolve()
    return driver, database


def believed(memory, recorded_as_of):
    """Alice→Bob reporting facts believed at a transaction time, with their valid-time bounds."""
    driver, database = memory
    fields = ", ".join(f'"{b}": $f.{b}' for b in BOUNDS)
    query = f"""
      match let $f in believed_at({recorded_as_of});
        $f isa reporting (report: $a, manager: $m); $a has gupi-id "p:alice"; $m has gupi-id "p:bob";
      fetch {{ "id": $f.gupi-id, {fields} }};
    """
    with transaction(driver, database, TransactionType.READ) as tx:
        docs = rows(tx, query)
    return {
        doc["id"]: ValidTime(*(doc[b] and datetime.fromisoformat(doc[b].replace("Z", "+00:00")) for b in BOUNDS))
        for doc in docs
    }


def test_believed_now_uses_the_correction(memory):
    facts = believed(memory, "2025-11-20T00:00:00Z")
    assert list(facts) == ["fact:r2"]
    vt = facts["fact:r2"]
    assert holds_at(vt, utc("2025-03-15T00:00:00")) is Truth.TRUE
    assert holds_at(vt, utc("2025-06-15T00:00:00")) is Truth.UNKNOWN  # month precision
    assert holds_at(vt, utc("2025-08-01T00:00:00")) is Truth.FALSE


def test_believed_in_march_was_open_ended_not_ongoing(memory):
    facts = believed(memory, "2025-03-15T00:00:00Z")
    assert list(facts) == ["fact:r1"]
    vt = facts["fact:r1"]
    assert holds_at(vt, utc("2025-01-05T00:00:00")) is Truth.TRUE
    # Back then the end was unknown: GUPI must not have claimed August was still true.
    assert holds_at(vt, utc("2025-08-01T00:00:00")) is Truth.UNKNOWN


def test_nothing_believed_before_anything_was_recorded(memory):
    assert believed(memory, "2024-12-31T00:00:00Z") == {}


def test_history_is_kept_and_traceable_to_sources(memory):
    driver, database = memory
    with transaction(driver, database, TransactionType.READ) as tx:
        old = rows(tx, 'match $f isa reporting, has gupi-id "fact:r1"; '
                       'supersession (superseded: $f, replacement: $n); $n has gupi-id $nid;')
        sources = rows(tx, 'match $f isa fact, has gupi-id "fact:r2"; evidence (supported: $f, support: $o); '
                           '$o has gupi-id $oid; sourcing (source: $s, observed: $o); $s has gupi-id $sid;')
    assert [r.get("nid").get_string() for r in old] == ["fact:r2"]
    assert sorted(r.get("oid").get_string() for r in sources) == ["obs:1", "obs:2"]
    assert {r.get("sid").get_string() for r in sources} == {"src:hr-notes"}
