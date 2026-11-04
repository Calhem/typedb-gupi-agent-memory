"""Claimant identity (docs/evaluation/phase-7b/contract-corrections.md, "Organisational claimants").

Individual and forwarded-from-a-person claimants are represented correctly today. Organisational and unknown
claimants are not: the persistence mapping makes every asserter a person (finding C2). Those cases are
strict expected failures until the proposed contract extension is approved; they define the behaviour."""

from datetime import datetime, timedelta, timezone

import pytest
from typedb.driver import TransactionType

from gupi import typeql
from gupi.formation import extractors, store
from gupi.records import Batch, Context, Observation, Source
from gupi.typedb.connection import transaction

pytestmark = pytest.mark.integration
SAID = datetime(2025, 8, 20, 9, tzinfo=timezone.utc)
C2 = pytest.mark.xfail(strict=True, reason="C2: the asserter is always created as a person (needs approval)")


def form_one(memory, clock, text, approve=False):
    clock.now = SAID
    obs = Observation("src:cl", "k1", text, SAID, "ctx:cl")
    memory.ingest(Batch((Source("src:cl", "mail"),), (obs,), contexts=(Context("ctx:cl", "conversation"),)))
    cset, _ = extractors.get("rules:v2.1").extract(obs)
    clock.now = SAID + timedelta(minutes=1)
    store.submit(memory, obs, cset)
    s = store.get(memory, cset.candidates[0].id)
    if approve and s.status == "review":
        clock.now += timedelta(minutes=1)
        store.review(memory, s.candidate.id, "approve", "reviewer-a")
        s = store.get(memory, s.candidate.id)
    return s


def asserter(memory, claim_id):
    """(kind, label) of the claim's asserter, or None."""
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        docs = typeql.documents(tx, "match $c isa claim, has gupi-id == $id; assertion (asserter: $a, asserted: $c); "
                                    "$a isa! $t; $a has label $l; fetch { 'kind': $t, 'label': $l };", {"id": claim_id})
    if not docs:
        return None
    (d,) = docs
    return d["kind"]["label"], d["label"]


def test_an_individual_claimant_is_a_person(memory, clock):
    s = form_one(memory, clock, "According to Dana Okoro, Mara Quist joined Pellwick in May 2025.")
    assert s.status == "formed" and s.candidate.attribution.mode == "reported"
    assert asserter(memory, s.claim_id) == ("person", "Dana Okoro")


def test_a_statement_forwarded_from_a_person_keeps_that_person_as_claimant(memory, clock):
    text = "FYI.\n---- Forwarded message ----\nFrom: Dana Okoro\nMara Quist has reported to Ivo Marsh since April 2025."
    s = form_one(memory, clock, text)
    assert s.candidate.attribution.mode == "forwarded" and s.candidate.attribution.asserted_by == "Dana Okoro"
    assert asserter(memory, s.claim_id) == ("person", "Dana Okoro")


def test_an_unknown_claimant_creates_no_invented_asserter(memory, clock):
    s = form_one(memory, clock, "Reportedly Mara Quist works at Pellwick.", approve=True)
    assert s.candidate.attribution.mode == "rumour" and s.candidate.attribution.asserted_by is None
    assert s.status == "formed" and asserter(memory, s.claim_id) is None


@C2
def test_an_organisational_claimant_is_not_made_a_person(memory, clock):
    s = form_one(memory, clock, "According to Halden Press, Mara Quist joined Pellwick in May 2025.")
    assert asserter(memory, s.claim_id) == ("organization", "Halden Press")


@C2
def test_a_claimant_of_unknown_kind_is_not_assumed_to_be_a_person(memory, clock):
    """Nothing in "According to Quill, ..." says whether Quill is a person or an organisation."""
    s = form_one(memory, clock, "According to Quill, Mara Quist joined Pellwick in May 2025.")
    assert asserter(memory, s.claim_id)[0] == "unclassified"
