"""Idempotent, all-or-nothing ingestion against the live server."""

import pytest
from helpers import CHAT, HR, PEOPLE, WIKI, observe, record, reports, utc
from typedb.driver import TransactionType

from gupi import typeql
from gupi.memory import ConflictError, Memory
from gupi.records import Batch, Claim, Evidence, Referent
from gupi.typedb.connection import transaction

pytestmark = pytest.mark.integration

COUNTED = ["source", "observation", "referent", "claim", "evidence", "sourcing", "review"]


def counts(memory):
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        return {t: len(typeql.concept_rows(tx, f"match $x isa {t};")) for t in COUNTED}


def batch_one():
    hr = observe(HR, "hr-1", "Alice reports to Bob.", "2025-01-05")
    chat = observe(CHAT, "msg-1", "Alice reports to Bob.", "2025-01-06")  # same words, other source
    return [hr, chat], [reports(hr), reports(chat)]


def test_reingesting_the_same_data_creates_nothing(memory, clock):
    observations, claims = batch_one()
    clock.set("2025-01-10")
    first = record(memory, observations, claims)
    after_first = counts(memory)
    clock.set("2025-03-01")
    second = record(memory, observations, claims)

    assert second.created == [] and sorted(second.existing) == sorted(first.created)
    assert counts(memory) == after_first
    assert after_first == {"source": 2, "observation": 2, "referent": len(PEOPLE), "claim": 2,
                           "evidence": 2, "sourcing": 2, "review": 0}
    # Re-ingesting later does not move transaction time.
    assert memory.claim(claims[0].id).recorded_at == utc("2025-01-10")


def test_multiple_sources_keep_separate_observations_and_claims(memory, clock):
    observations, claims = batch_one()
    record(memory, observations, claims)
    sources = {c.id: {e.source_id for e in memory.claim(c.id).evidence} for c in claims}
    assert sources == {claims[0].id: {"src:hr"}, claims[1].id: {"src:chat"}}


def test_interrupted_transaction_leaves_nothing_behind(driver, database, clock):
    class Crashing(Memory):
        def _before_claims(self, tx):
            raise RuntimeError("simulated crash half-way through a batch")

    crashing = Crashing.open(database, packs=("core", "people"), driver=driver, clock=clock)
    observations, claims = batch_one()
    with pytest.raises(RuntimeError):
        record(crashing, observations, claims)
    healthy = Memory(driver, database, clock)
    assert set(counts(healthy).values()) == {0}

    report = record(healthy, observations, claims)
    assert len(report.created) == 2 + 2 + len(PEOPLE) + 2
    assert record(healthy, observations, claims).created == []


def test_interrupted_run_of_batches_resumes_without_duplicates(memory, clock):
    observations, claims = batch_one()
    good = Batch((HR, CHAT), tuple(observations), PEOPLE, tuple(claims))
    wiki = observe(WIKI, "w-1", "Alice reports to Bob.", "2025-01-07")
    broken = Batch((WIKI,), (wiki,), (), (reports(wiki, manager="p:nobody"),))
    with pytest.raises(ValueError, match="unknown referent"):
        memory.ingest_many([good, broken])
    assert counts(memory)["claim"] == 2  # the first batch committed, the second did not

    fixed = Batch((WIKI,), (wiki,), (), (reports(wiki),))
    reports_ = memory.ingest_many([good, fixed])
    assert reports_[0].created == [] and len(reports_[1].created) == 3
    assert counts(memory)["claim"] == 3 and counts(memory)["observation"] == 3


def test_conflicting_referent_type_aborts_the_whole_batch(memory):
    record(memory, [], [])
    before = counts(memory)
    obs = observe(HR, "hr-2", "Acme is a person?", "2025-01-05")
    with pytest.raises(ConflictError):
        memory.ingest(Batch((HR,), (obs,), (Referent("o:acme", "person"),), ()))
    assert counts(memory) == before


def test_references_and_types_are_checked(memory):
    record(memory, [], [])
    obs = observe(HR, "hr-3", "Alice reports to Bob.", "2025-01-05")
    with pytest.raises(ValueError, match="unknown observation"):
        memory.ingest(Batch(claims=(Claim("reporting", {"report": "p:alice", "manager": "p:bob"},
                                          (Evidence("obs:missing"),)),)))
    with pytest.raises(ValueError, match="unknown source"):
        memory.ingest(Batch(observations=(obs,)))
    with pytest.raises(ValueError, match="not a claim type"):
        memory.ingest(Batch(claims=(Claim("friendship", {"friend": "p:alice"}, (Evidence(obs.id),)),)))


def test_hostile_text_is_stored_verbatim_and_never_executed(memory, clock):
    nasty = 'x"; } ; match $c isa claim; delete $c; insert $y isa source, has gupi-id "pwned'
    obs = observe(HR, nasty, nasty, "2025-01-05")
    c = reports(obs)
    record(memory, [obs], [c])
    view = memory.claim(c.id)
    assert view.evidence[0].content == nasty and view.evidence[0].quote == nasty
    assert counts(memory)["source"] == 1 and counts(memory)["claim"] == 1
