"""C2 (docs/evaluation/phase-7b/stage-2b/claimant-classification.md): claimants are persisted with the kind
the evidence establishes, never as people by default; claimant identity and kind stay distinct."""

from datetime import datetime, timedelta, timezone

import pytest
from typedb.driver import TransactionType

from gupi import ids, typeql
from gupi.formation import extractors, store
from gupi.formation.candidate import (
    IR_VERSION_1_1, Attribution, Candidate, CandidateSet, Participant, Passage, TimeEvidence,
)
from gupi.records import Batch, Context, Observation, Referent, Source
from gupi.typedb.connection import transaction

pytestmark = pytest.mark.integration
SAID = datetime(2025, 8, 20, 9, tzinfo=timezone.utc)
S8 = pytest.mark.xfail(strict=True, reason="S8: same-named referents in one conversation share an identity (no evidence to tell them apart)")


def ingest(memory, clock, text, key, context="ctx:c2", author=("p:ivo", "person", "Ivo Marsh")):
    clock.now = SAID + timedelta(minutes=len(key))
    obs = Observation("src:c2", key, text, clock.now, context, author[0] if author else None)
    refs = (Referent(*author),) if author else ()
    memory.ingest(Batch((Source("src:c2", "mail"),), (obs,), refs, contexts=(Context(context, "conversation"),)))
    return obs


def candidate(obs, claimant=None, kind=None, mode="reported", via=()):
    t = obs.content
    who, org = "Mara Quist", "Pellwick"
    ps, os_ = t.rindex(who), t.rindex(org)
    m = t.rindex("May 2025")
    return Candidate("employment", Passage(obs.id, 0, len(t), t),
                     (Participant("employee", who, ps, ps + len(who), "person"), Participant("employer", org, os_, os_ + len(org), "organization")),
                     times=(TimeEvidence("start", "May 2025", m, m + 8, datetime(2025, 5, 1, tzinfo=timezone.utc),
                                         datetime(2025, 6, 1, tzinfo=timezone.utc), "month"),),
                     attribution=Attribution(claimant, mode, tuple(via), ("forwarded",) if mode == "forwarded" else (), kind))


def submit(memory, clock, obs, c, version=IR_VERSION_1_1):
    clock.now += timedelta(seconds=30)
    cs = CandidateSet(obs.id, ids.content_hash(obs.content), "test", (c,), version)
    store.submit(memory, obs, cs)
    s = store.get(memory, c.id)
    assert s is not None and s.status == "formed", s and s.decisions
    return s.claim_id


def asserter(memory, claim_id):
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        docs = typeql.documents(tx, "match $c isa claim, has gupi-id == $id; assertion (asserter: $a, asserted: $c); "
                                    "$a isa! $t; $a has label $l, has gupi-id $aid; "
                                    "fetch { 'kind': $t, 'label': $l, 'id': $aid };", {"id": claim_id})
    return [(d["kind"]["label"], d["label"], d["id"]) for d in docs]


def kinds(memory, label):
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        docs = typeql.documents(tx, "match $a isa! $t, has label == $l; $t sub referent; fetch { 'kind': $t };", {"l": label})
    return sorted(d["kind"]["label"] for d in docs)


def test_a_named_individual(memory, clock):
    o = ingest(memory, clock, "According to Dana Okoro, Mara Quist joined Pellwick in May 2025.", "a")
    claim = submit(memory, clock, o, candidate(o, "Dana Okoro", "person"))
    assert [(k, l) for k, l, _ in asserter(memory, claim)] == [("person", "Dana Okoro")]


def test_an_organisation_issuing_a_statement(memory, clock):
    o = ingest(memory, clock, "Halden Press announced that Mara Quist joined Pellwick in May 2025.", "b")
    claim = submit(memory, clock, o, candidate(o, "Halden Press", "organisation"))
    assert [(k, l) for k, l, _ in asserter(memory, claim)] == [("organization", "Halden Press")]
    assert kinds(memory, "Halden Press") == ["organization"]                 # never also a person


def test_a_news_organisation_reporting_a_persons_assertion(memory, clock):
    o = ingest(memory, clock, "Halden Press reports that Dana Okoro said Mara Quist joined Pellwick in May 2025.", "cc")
    claim = submit(memory, clock, o, candidate(o, "Dana Okoro", "person", via=("p:ivo", "Halden Press")))
    assert [(k, l) for k, l, _ in asserter(memory, claim)] == [("person", "Dana Okoro")]
    assert kinds(memory, "Halden Press") == []                               # an intermediary, not invented as anyone
    assert store.get(memory, candidate(o, "Dana Okoro", "person", via=("p:ivo", "Halden Press")).id).candidate.attribution.via == \
        ("p:ivo", "Halden Press")                                            # the chain stays traceable


def test_a_person_forwarding_an_organisational_statement(memory, clock):
    text = "FYI.\n---- Forwarded message ----\nFrom: Halden Press Office\nMara Quist joined Pellwick in May 2025."
    o = ingest(memory, clock, text, "ddd")
    claim = submit(memory, clock, o, candidate(o, "Halden Press Office", "organisation", mode="forwarded", via=("p:ivo",)))
    assert [(k, l) for k, l, _ in asserter(memory, claim)] == [("organization", "Halden Press Office")]  # not the forwarder


def test_an_organisation_forwarding_another_organisations_statement(memory, clock):
    text = "Passing on.\n---- Forwarded message ----\nFrom: Halden Press Office\nMara Quist joined Pellwick in May 2025."
    o = ingest(memory, clock, text, "eeee", author=("o:pellwick-comms", "organization", "Pellwick Communications"))
    claim = submit(memory, clock, o, candidate(o, "Halden Press Office", "organisation", mode="forwarded", via=("o:pellwick-comms",)))
    assert [(k, l) for k, l, _ in asserter(memory, claim)] == [("organization", "Halden Press Office")]
    assert kinds(memory, "Pellwick Communications") == ["organization"]


def test_an_unidentified_claimant_creates_no_asserter(memory, clock):
    o = ingest(memory, clock, "Reportedly Mara Quist joined Pellwick in May 2025.", "fffff")
    c = candidate(o, None, None, mode="rumour")
    clock.now += timedelta(seconds=30)
    store.submit(memory, o, CandidateSet(o.id, ids.content_hash(o.content), "test", (c,), IR_VERSION_1_1))
    clock.now += timedelta(seconds=30)
    store.review(memory, c.id, "approve", "reviewer-a")
    assert asserter(memory, store.get(memory, c.id).claim_id) == []


def test_an_unknown_kind_stays_unknown(memory, clock):
    o = ingest(memory, clock, "According to Quill, Mara Quist joined Pellwick in May 2025.", "gggggg")
    claim = submit(memory, clock, o, candidate(o, "Quill", "unknown"))
    assert [(k, l) for k, l, _ in asserter(memory, claim)] == [("unclassified", "Quill")]


def test_a_legacy_1_0_claimant_without_a_kind_is_not_made_a_person(memory, clock):
    """rules:v2.1 emits format 1.0, with no claimant kind: the claimant's kind is not established."""
    o = ingest(memory, clock, "According to Dana Okoro, Mara Quist joined Pellwick in May 2025.", "hhhhhhh")
    cset, _ = extractors.get("rules:v2.1").extract(o)
    clock.now += timedelta(seconds=30)
    store.submit(memory, o, cset)
    claim = store.get(memory, cset.candidates[0].id).claim_id
    assert cset.ir_version == "gupi.candidate/1"
    assert [(k, l) for k, l, _ in asserter(memory, claim)] == [("unclassified", "Dana Okoro")]


def test_same_named_people_in_different_conversations_are_distinct(memory, clock):
    a = ingest(memory, clock, "According to Dana Okoro, Mara Quist joined Pellwick in May 2025.", "i", context="ctx:one")
    b = ingest(memory, clock, "According to Dana Okoro, Mara Quist joined Pellwick in May 2025.", "ii", context="ctx:two")
    ids_ = {asserter(memory, submit(memory, clock, o, candidate(o, "Dana Okoro", "person")))[0][2] for o in (a, b)}
    assert len(ids_) == 2


@S8
def test_same_named_people_in_one_conversation_are_not_merged(memory, clock):
    a = ingest(memory, clock, "According to Dana Okoro, Mara Quist joined Pellwick in May 2025.", "j")
    b = ingest(memory, clock, "Separately, according to Dana Okoro, Mara Quist joined Pellwick in May 2025.", "jj")
    ids_ = {asserter(memory, submit(memory, clock, o, candidate(o, "Dana Okoro", "person")))[0][2] for o in (a, b)}
    assert len(ids_) == 2   # nothing in the text says these are different people, so they cannot be told apart


def test_a_person_and_an_organisation_with_the_same_name_stay_distinct(memory, clock):
    a = ingest(memory, clock, "According to Morgan Grey, Mara Quist joined Pellwick in May 2025.", "k")
    b = ingest(memory, clock, "Morgan Grey (the agency) says Mara Quist joined Pellwick in May 2025.", "kk")
    pa = asserter(memory, submit(memory, clock, a, candidate(a, "Morgan Grey", "person")))[0]
    pb = asserter(memory, submit(memory, clock, b, candidate(b, "Morgan Grey", "organisation")))[0]
    assert pa[0] == "person" and pb[0] == "organization" and pa[2] != pb[2]
    assert kinds(memory, "Morgan Grey") == ["organization", "person"]


def test_claimant_identity_and_kind_are_not_merged_without_review(memory, clock):
    """An unclassified claimant and a person of the same name are two referents; identity is only a
    suggestion until a reviewer accepts it."""
    o = ingest(memory, clock, "According to Mara Quist, Mara Quist joined Pellwick in May 2025.", "l")
    cset, _ = extractors.get("rules:v2.1").extract(o)
    clock.now += timedelta(seconds=30)
    store.submit(memory, o, cset)
    assert kinds(memory, "Mara Quist") == ["person", "unclassified"]
    assert not memory.identity_groups(clock.now) or all(len(g) == 1 for g in memory.identity_groups(clock.now).values())
