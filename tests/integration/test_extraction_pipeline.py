"""The extraction contract and pipeline on the live server, with canned (fixture) extractor output."""

import pytest
from helpers import CHAT, utc

from gupi.extraction.pipeline import FixtureExtractor, extract
from gupi.records import Batch, Context, Observation
from gupi.status import Status
from gupi.temporal import Answer

pytestmark = pytest.mark.integration

CONVO = Context("conv:9", "conversation")
TEXT = "Alice has reported to Bob since March 2024. She is learning Rust."
MSG = Observation(CHAT.id, "msg-1", TEXT, utc("2025-11-14T16:00"), context_id=CONVO.id)
MENTIONS = [{"id": "m1", "text": "Alice", "start": 0, "end": 5, "kind": "person"},
            {"id": "m2", "text": "Bob", "start": 22, "end": 25, "kind": "person"}]


def output(*claims, mentions=MENTIONS):
    return {TEXT: {"mentions": mentions, "claims": list(claims)}}


def reporting(**overrides):
    c = {"type": "reporting", "roles": {"report": ["m1"], "manager": ["m2"]}, "values": {},
         "quote": "Alice has reported to Bob since March 2024.", "start": 0, "end": 43,
         "basis": "explicit", "confidence": 0.9, "time": {"start": "March 2024", "end": None, "ongoing": True}}
    return {**c, **overrides}


@pytest.fixture
def ingested(memory):
    memory.ingest(Batch((CHAT,), (MSG,), contexts=(CONVO,)))
    return memory


def test_typed_claim_is_recorded_as_a_hypothesis_with_grounded_time(ingested, clock):
    fx = FixtureExtractor(output(reporting()))
    result = extract(ingested, fx, [MSG])
    assert len(result.claims) == 1 and result.rejected == []
    claim = ingested.claim(result.claims[0])
    assert claim.type == "reporting" and claim.basis == "explicit" and claim.method == "fixture:v1"
    assert claim.status_at(clock()) is Status.HYPOTHESIS  # never accepted automatically
    assert (claim.valid.from_earliest, claim.valid.from_latest) == (utc("2024-03"), utc("2024-04"))
    assert claim.valid.to_earliest == MSG.observed_at and claim.valid_to_basis == "ongoing-at-observation"
    assert claim.evidence[0].quote == "Alice has reported to Bob since March 2024."
    alice = claim.roles["report"][0]
    assert ingested.ask("reporting", {"report": alice, "manager": claim.roles["manager"][0]},
                        utc("2025-01")).answer is Answer.UNKNOWN  # recorded, not believed

    again = extract(ingested, fx, [MSG])
    assert again.skipped == [MSG.id] and fx.calls == 1  # re-running does not call the extractor again


def test_generic_statement_is_kept_provisional_and_mapped_when_a_typed_claim_exists(ingested):
    learning = {"type": "statement", "roles": {"subject": ["m1"]}, "predicate": "Is learning",
                "object_text": "Rust", "quote": "She is learning Rust.", "basis": "explicit",
                "time": {"ongoing": True}}
    mapped = {"type": "statement", "roles": {"subject": ["m1"], "object": ["m2"]}, "predicate": "reports to",
              "quote": "Alice has reported to Bob", "basis": "inferred"}
    result = extract(ingested, FixtureExtractor(output(learning, mapped)), [MSG])
    views = {v.type: v for v in map(ingested.claim, result.claims)}
    assert set(views) == {"statement", "reporting"}
    assert views["statement"].provisional and views["statement"].values == {
        "predicate-text": "is learning", "object-text": "Rust"}
    assert views["reporting"].basis == "inferred" and not views["reporting"].provisional
    assert any("converted to typed claim reporting" in n for n in result.notes)


@pytest.mark.parametrize("bad, reason", [
    (reporting(quote="Alice reports to Bob"), "quote does not match"),
    (reporting(type="friendship"), "not available"),
    (reporting(type="identity"), "not available"),
    (reporting(roles={"boss": ["m2"]}), "no role"),
    (reporting(roles={"report": ["m9"]}), "unknown or rejected mention"),
    (reporting(basis="guess"), "basis"),
    (reporting(values={"job-title": "CTO"}), "no attribute"),
    (reporting(confidence=3), "confidence"),
    ({"type": "statement", "roles": {"object": ["m2"]}, "predicate": "likes", "quote": TEXT, "basis": "explicit"},
     "needs a subject"),
    ({"type": "statement", "roles": {"subject": ["m1"]}, "quote": TEXT, "basis": "explicit"}, "needs a predicate"),
])
def test_invalid_claims_are_rejected_with_a_reason(ingested, bad, reason):
    result = extract(ingested, FixtureExtractor(output(bad)), [MSG])
    assert result.claims == [] and len(result.rejected) == 1 and reason in result.rejected[0][2]


def test_ungrounded_dates_and_bad_mentions_are_not_trusted(ingested):
    invented = reporting(time={"start": "1 January 2020", "end": "2025-06-30", "ongoing": False})
    mentions = MENTIONS + [{"id": "m3", "text": "Carol", "start": 0, "end": 5, "kind": "person"},
                           {"id": "m4", "text": "Rust", "start": 61, "end": 65, "kind": "language"}]
    result = extract(ingested, FixtureExtractor(output(invented, mentions=mentions)), [MSG])
    claim = ingested.claim(result.claims[0])
    assert claim.valid.from_earliest is None and claim.valid.to_latest is None and claim.valid_to_basis == "unknown"
    assert sum("not in the source text" in n for n in result.notes) == 2
    assert [r[1] for r in result.rejected] == ["mention 'Carol'"]
    assert any("recorded as unclassified" in n for n in result.notes)  # unknown kind: no schema evolution


def test_referents_are_scoped_to_their_conversation(memory):
    other = Context("conv:10", "conversation")
    msg2 = Observation(CHAT.id, "msg-2", TEXT, utc("2025-11-15"), context_id=other.id)
    memory.ingest(Batch((CHAT,), (MSG, msg2), contexts=(CONVO, other)))
    result = extract(memory, FixtureExtractor({TEXT: output(reporting())[TEXT]}), [MSG, msg2])
    alices = {memory.claim(c).roles["report"][0] for c in result.claims}
    assert len(alices) == 2  # same name, two conversations: not merged


def test_run_report_distinguishes_explicit_and_inferred_dates(ingested):
    """The extraction run records, per claim and bound, whether the date was stated or inferred."""
    import json
    from gupi import typeql
    from gupi.typedb.connection import transaction
    from typedb.driver import TransactionType
    text = "Alice has reported to Bob since March 2024. She is learning Rust."  # March 2024: explicit
    result = extract(ingested, FixtureExtractor(output(reporting())), [MSG])
    with transaction(ingested.driver, ingested.database, TransactionType.READ) as tx:
        (doc,) = typeql.documents(tx, 'match $r isa extraction-run; fetch { "report": $r.run-report };')
    times = json.loads(doc["report"])["times"]
    assert times == [{"claim": result.claims[0], "bound": "start", "phrase": "March 2024", "read": True,
                      "explicit": True, "assumption": None}]
    assert text == MSG.content  # source text preserved verbatim
