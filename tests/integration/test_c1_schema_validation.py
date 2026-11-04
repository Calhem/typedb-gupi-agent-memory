"""C1 (docs/evaluation/phase-7b/contract-corrections.md): schema-aware validation and the candidate store
apply the same admissibility rules, and a well-formed generic statement is valid under both."""

from datetime import timedelta

import pytest
from typedb.driver import TransactionType

from gupi import ids
from gupi.extraction.contract import SchemaInfo
from gupi.formation import evaluation, extractors, store
from gupi.formation.candidate import Candidate, CandidateSet, Participant, Passage
from gupi.formation.validate import validate
from gupi.records import Batch, Context, Observation, Source
from gupi.typedb.connection import transaction

pytestmark = pytest.mark.integration
TEXT = "Halden Holdings owns Pellwick."


def schema_of(memory):
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        return SchemaInfo.load(tx, ("core", "people"))


def statement(obs, values=(("predicate-text", "owns"),), participants=None, claim_type="statement"):
    parts = participants or (Participant("subject", "Halden Holdings", 0, 15, "organization"),
                             Participant("object", "Pellwick", 21, 29, "organization"))
    c = Candidate(claim_type, Passage(obs.id, 0, len(obs.content), obs.content), parts, tuple(values))
    return CandidateSet(obs.id, ids.content_hash(obs.content), "test", (c,))


def observation(memory, clock, text=TEXT):
    obs = Observation("src:c1", "k" + ids.content_hash(text)[:6], text, clock(), "ctx:c1")
    memory.ingest(Batch((Source("src:c1", "test"),), (obs,), contexts=(Context("ctx:c1", "conversation"),)))
    return obs


def codes(cset, obs, schema):
    return sorted({i.code for i in validate(cset, obs, schema)})


def test_a_well_formed_statement_is_valid_with_the_schema(memory, clock):
    obs = observation(memory, clock)
    assert codes(statement(obs), obs, schema_of(memory)) == []
    subject_only = (Participant("subject", "Halden Holdings", 0, 15, "organization"),)
    assert codes(statement(obs, (("object-text", "a stake in Pellwick"), ("predicate-text", "owns")), subject_only),
                 obs, schema_of(memory)) == []
    assert codes(statement(obs, (("predicate-text", "owns"),), subject_only), obs, schema_of(memory)) == []  # object optional


@pytest.mark.parametrize("values, participants, claim_type, code", [
    ((), None, "statement", "statement"),                                        # no predicate
    ((("predicate-text", "owns"), ("predicate-text", "controls")), None, "statement", "statement"),  # two predicates
    ((("predicate-text", "owns"),), (Participant("object", "Pellwick", 21, 29, "organization"),), "statement", "statement"),
    ((("predicate-text", "owns"),), (Participant("owner", "Halden Holdings", 0, 15, "organization"),), "statement", "schema"),
    ((("commitment", "certain"), ("predicate-text", "owns")), None, "statement", "value"),   # a field formation sets
    ((("predicate-text", "owns"),), (Participant("employee", "Halden Holdings", 0, 15, "person"),
                                     Participant("employer", "Pellwick", 21, 29, "organization")), "employment", "value"),
])
def test_malformed_statements_and_misplaced_values_are_rejected(memory, clock, values, participants, claim_type, code):
    obs = observation(memory, clock)
    assert code in codes(statement(obs, values, participants, claim_type), obs, schema_of(memory))


def test_the_store_applies_the_live_schema(memory, clock):
    """Admissibility is the same in the store as in schema-aware validation: an employer that is a person is
    refused at submit even when the caller passes no schema."""
    text = "Nora Vance works at Ivo Marsh."
    obs = observation(memory, clock, text)
    bad = Candidate("employment", Passage(obs.id, 0, len(text), text),
                    (Participant("employee", "Nora Vance", 0, 10, "person"), Participant("employer", "Ivo Marsh", 20, 29, "person")))
    cset = CandidateSet(obs.id, ids.content_hash(text), "test", (bad,))
    assert "schema" in codes(cset, obs, schema_of(memory))
    clock.now = clock.now + timedelta(minutes=1)
    result = store.submit(memory, obs, cset)
    assert result.stored == [] and result.invalid and not memory.all_claims()


def test_a_valid_statement_is_stored_and_formed(memory, clock):
    obs = observation(memory, clock)
    clock.now = clock.now + timedelta(minutes=1)
    cset = statement(obs)
    store.submit(memory, obs, cset)
    s = store.get(memory, cset.candidates[0].id)
    assert s.status == "formed" and memory.claims([s.claim_id])[0].values == {"predicate-text": "owns"}


def test_existing_rules_candidates_remain_valid_with_the_schema(memory):
    schema = schema_of(memory)
    data = evaluation.load()
    for version in ("rules:v2", "rules:v2.1"):
        for p, obs in evaluation.observations(data):
            cset, _ = extractors.get(version).extract(obs)
            assert validate(cset, obs, schema) == [], (version, p["id"])
