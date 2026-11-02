"""Phase 2 schema: contexts, mentions, extraction basis and the provisional generic `statement` claim."""

import pytest
from helpers import CHAT, PEOPLE, observe
from typedb.driver import TransactionType

from gupi import typeql
from gupi.records import Batch, Claim, Context, Evidence, Mention, Observation
from gupi.status import Status
from gupi.typedb.connection import transaction

pytestmark = pytest.mark.integration

CONVO = Context("conv:1", "conversation", "Team chat, 1 Oct")


def message(key, text, when="2025-10-01"):
    o = observe(CHAT, key, text, when)
    return Observation(o.source_id, o.record_key, o.content, o.observed_at, context_id=CONVO.id)


def test_mentions_contexts_and_a_guarded_generic_statement(memory, clock):
    msg = message("m1", "Alice is learning Rust.")
    alice = Mention(msg.id, 0, 5, "Alice", "p:alice", confidence=0.9, method="extractor:fixture")
    stmt = Claim("statement", {"subject": "p:alice"}, (Evidence(msg.id, 0, 23),),
                 values={"predicate-text": "is learning", "object-text": "Rust"},
                 method="extractor:fixture", basis="explicit", confidence=0.7)
    report = memory.ingest(Batch((CHAT,), (msg,), PEOPLE, (stmt,), (CONVO,), (alice,)))
    assert {CONVO.id, msg.id, alice.id, stmt.id} <= set(report.created)

    view = memory.claim(stmt.id)
    assert view.provisional and view.basis == "explicit"
    assert view.values == {"predicate-text": "is learning", "object-text": "Rust"}
    assert view.roles == {"subject": ("p:alice",)} and view.evidence[0].quote == "Alice is learning Rust."
    assert view.status_at(clock()) is Status.HYPOTHESIS  # never accepted automatically

    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        refs = typeql.documents(tx, """
            match $c isa context, has gupi-id "conv:1"; containment (context: $c, member: $o);
                  mentioning (container: $o, mention: $m); $r isa reference (mention: $m, referent: $x);
            fetch { "surface": $m.surface-text, "referent": $x.gupi-id, "confidence": $r.confidence };""")
    assert refs == [{"surface": "Alice", "referent": "p:alice", "confidence": 0.9}]
    assert memory.ingest(Batch((CHAT,), (msg,), PEOPLE, (stmt,), (CONVO,), (alice,))).created == []


def test_mention_text_must_match_the_source(memory):
    msg = message("m2", "Bob joined.")
    memory.ingest(Batch((CHAT,), (msg,), PEOPLE, (), (CONVO,)))
    with pytest.raises(ValueError, match="does not match"):
        memory.ingest(Batch(mentions=(Mention(msg.id, 0, 3, "Rob", "p:bob"),)))


def test_generic_statement_needs_a_referent_subject_and_evidence(memory):
    msg = message("m3", "Rust is popular.")
    memory.ingest(Batch((CHAT,), (msg,), PEOPLE, (), (CONVO,)))
    with pytest.raises(ValueError, match="evidence"):
        Claim("statement", {"subject": "p:alice"}, ())
    with pytest.raises(ValueError, match="unknown referent"):  # a literal is not an identity
        memory.ingest(Batch(claims=(Claim("statement", {"subject": "Rust"}, (Evidence(msg.id),),
                                          values={"predicate-text": "is popular"}),)))
    with pytest.raises(Exception):  # a statement with no subject at all breaks `relates subject @card(1..)`
        memory.ingest(Batch(claims=(Claim("statement", {"object": "p:alice"}, (Evidence(msg.id),),
                                          values={"predicate-text": "is popular"}),)))


def test_unknown_context_is_refused(memory):
    msg = Observation(CHAT.id, "m4", "Hi", None, context_id="conv:missing")
    with pytest.raises(ValueError, match="unknown context"):
        memory.ingest(Batch((CHAT,), (msg,)))
