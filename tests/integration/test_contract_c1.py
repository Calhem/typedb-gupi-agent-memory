"""Finding C1 (docs/evaluation/phase-7b/candidate-contract-audit.md), demonstrated, not fixed: schema-aware
validation rejects a generic `statement` candidate's own predicate-text, while the store (which validates
without the schema by default) forms it. Strict expected failure until the contract is corrected."""

import pytest
from typedb.driver import TransactionType

from gupi import ids
from gupi.extraction.contract import SchemaInfo
from gupi.formation.candidate import Candidate, CandidateSet, Participant, Passage
from gupi.formation.validate import validate
from gupi.records import Observation
from gupi.typedb.connection import transaction

pytestmark = pytest.mark.integration


@pytest.mark.xfail(strict=True, reason="C1: SchemaInfo drops predicate-text/object-text, so statements fail schema validation")
def test_a_statement_with_predicate_text_passes_schema_aware_validation(memory, clock):
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        schema = SchemaInfo.load(tx, ("core", "people"))
    text = "Halden Holdings owns Pellwick."
    obs = Observation("src:c1", "k", text, clock(), "ctx:c1")
    c = Candidate("statement", Passage(obs.id, 0, len(text), text),
                  (Participant("subject", "Halden Holdings", 0, 15, "organization"),
                   Participant("object", "Pellwick", 21, 29, "organization")), (("predicate-text", "owns"),))
    assert validate(CandidateSet(obs.id, ids.content_hash(text), "test", (c,)), obs, schema) == []
