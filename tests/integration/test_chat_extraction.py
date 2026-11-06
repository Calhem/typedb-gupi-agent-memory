"""Automatic extraction through the protected path on a live TypeDB, with scripted replies: no model, no network."""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from helpers import Clock

from gupi.budget import Ledger
from gupi.formation import chat_extractor as chat
from gupi.formation import store
from gupi.formation.chat_extractor import ChatExtractor, Limits, Recording
from gupi.formation.form import live_schema
from gupi.formation.model_candidate import RESPONSE_FORMAT
from gupi.memory import Memory
from gupi.query import Question
from gupi.records import Batch, Context, Observation, Referent, Source
from gupi.temporal import Answer

pytestmark = pytest.mark.integration
SOURCE = Source("src:chat", "conversation", label="scripted chat")
JUNO = Referent("p:juno", "person", "Juno")
START = datetime(2023, 5, 8, 9, 0, tzinfo=timezone.utc)
DIRECT = {"mode": "direct", "claimant": None, "claimant_kind": None, "via": []}


def person(role, text, kind="person"):
    return {"role": role, "text": text, "kind": kind, "is_pronoun_or_vague": False}


def fact(evidence, participants, **over):
    return {"evidence": evidence, "evidence_occurrence": None, "relation": "statement", "participants": participants,
            "times": [], "polarity": "positive", "modality": "actual", "commitment": "certain", "basis": "explicit",
            "attribution": DIRECT, "predicate": None, "object_text": None, "title": None, "allegation": None,
            "correction": None} | over


JOIN = fact("Bram Oster joined Fenwick Labs in 2021",
            [person("employee", "Bram Oster"), person("employer", "Fenwick Labs", "organization")],
            relation="employment", times=[{"text": "2021", "kind": "start"}])
ALLEGED = fact("Bram Oster stole the prototype", [person("subject", "Bram Oster")], predicate="stole",
               object_text="the prototype", allegation=True)
PLAN = fact("I will adopt a greyhound", [person("subject", "I")], predicate="adopt", object_text="a greyhound",
            modality="planned")
EVENT = fact("I ran the Oslo race last week", [person("subject", "I")], predicate="ran", object_text="the Oslo race",
             times=[{"text": "last week", "kind": "holds-at"}])
FIXED = fact("Bram Oster joined Fenwick Labs in 2022",
             [person("employee", "Bram Oster"), person("employer", "Fenwick Labs", "organization")], relation="employment",
             times=[{"text": "2022", "kind": "start"}], correction={"kind": "corrects", "cue": "Correction", "earlier_statement": None})
TURNS = [("Bram Oster joined Fenwick Labs in 2021.", [JOIN]),
         ("Rumour: Bram Oster stole the prototype.", [ALLEGED]),
         ("I will adopt a greyhound.", [PLAN]),
         ("I ran the Oslo race last week.", [EVENT]),
         ("Correction: Bram Oster joined Fenwick Labs in 2022.", [FIXED]),
         ("Good morning!", [])]


def reply(assertions):
    text = json.dumps({"format": RESPONSE_FORMAT, "outcome": "assertions" if assertions else "no-relevant-assertion",
                       "assertions": assertions, "problems": []})
    return {"model": "gpt-4o-mini-2024-07-18", "choices": [{"finish_reason": "stop", "message": {"content": text}}],
            "usage": {"prompt_tokens": 1500, "completion_tokens": 100}}


class Scripted:
    """Answers by message text, as a recording would: the request decides the reply."""

    def __init__(self):
        self.calls = 0

    def __call__(self, body):
        self.calls += 1
        user = body["messages"][1]["content"]
        message = user.split("<message>\n")[1].split("\n</message>")[0]
        return reply(dict(TURNS)[message])


def run(memory, clock, extractor):
    context, prior, before, observations = Context("s1", "session"), (), [], []
    schema = live_schema(memory)
    for n, (text, _) in enumerate(TURNS):
        clock.now = max(clock.now, START + timedelta(minutes=n))
        o = Observation(SOURCE.id, f"t{n}", text, START + timedelta(minutes=n), context.id, JUNO.id)
        memory.ingest(Batch((SOURCE,), (o,), (JUNO,), contexts=(context,)))
        observations.append(o)
        cset, _ = extractor.extract(o, JUNO.label, tuple(before), prior, schema)
        prior += (cset,)
        before.append((JUNO.label, text))
        clock.now += timedelta(seconds=1)
        extractor.submit(memory, o, cset)
    return observations


@pytest.fixture
def ledger(driver):
    name = f"gupi-test-ledger-{uuid.uuid4().hex[:8]}"
    yield Ledger(driver, name, limit_usd=0.05, run_cap_usd=0.04, clock=Clock())
    driver.databases.get(name).delete()


def live(tmp_path, ledger):
    return ChatExtractor(Recording(tmp_path / "r.jsonl"), Scripted(), ledger, Limits(max_calls=20))


def claims_by_evidence(memory):
    return {c.evidence[0].quote: c for c in memory.all_claims()}


def test_a_session_flows_through_the_protected_path(memory, clock, ledger, tmp_path):
    e = live(tmp_path, ledger)
    observations = run(memory, clock, e)
    t = e.tally
    assert t.messages == 6 and t.calls == 6 and not t.failures
    assert t.decisions == {"formed": 1, "review": 2, "withheld": 2}
    assert t.withheld_for_time == 1          # the known one-time-event gap, counted rather than worked around
    assert t.outcomes["no-relevant-assertion"] == 1
    assert ledger.spent_microusd() == t.charged_microusd == 6 * 285

    stored = store.pending(memory)
    assert {s.candidate.commitment for s in stored} >= {"unknown"}
    assert len(memory.all_claims()) == 1
    claim = memory.all_claims()[0]
    assert claim.type == "employment" and claim.basis == "explicit"
    assert claim.evidence[0].observation_id == observations[0].id
    assert claim.method.startswith("model:candidate-v1.1:gpt-4o-mini:")


def test_raw_conversation_survives_beside_claims(memory, clock, ledger, tmp_path):
    observations = run(memory, clock, live(tmp_path, ledger))
    assert [store._observation(memory, o.id).content for o in observations] == [text for text, _ in TURNS]
    stored = store.get(memory, store.pending(memory)[0].candidate.id)
    assert stored.observation_id in {o.id for o in observations}
    assert stored.extractor.startswith("model:candidate-v1.1:gpt-4o-mini:")


def test_time_stays_uncertain_and_is_answered_by_the_existing_model(memory, clock, ledger, tmp_path):
    run(memory, clock, live(tmp_path, ledger))
    c = memory.all_claims()[0]
    roles = {k: v[0] for k, v in c.roles.items()}
    assert c.time_precision == "year"
    at = datetime(2021, 6, 1, tzinfo=timezone.utc)      # inside the stated year: unknown, never a guessed yes
    assert memory.query(Question("employment", roles, at, semantics="v2")).answer is Answer.UNKNOWN


def test_nothing_supersedes_or_approves_itself(memory, clock, ledger, tmp_path):
    run(memory, clock, live(tmp_path, ledger))
    assert not any(c.superseded_by for c in memory.all_claims())
    pending = store.pending(memory)
    correction = next(s for s in pending if s.candidate.relations)
    assert correction.candidate.relations[0].kind == "corrects"
    assert all(d.decided_by == "formation:v1" for s in pending for d in s.decisions)
    assert next(s for s in pending if not s.candidate.relations).candidate.commitment == "unknown"   # the allegation


def test_replay_rebuilds_the_same_memory_without_a_model_or_a_ledger(driver, memory, clock, ledger, tmp_path):
    first = live(tmp_path, ledger)
    run(memory, clock, first)
    name = f"gupi-test-{uuid.uuid4().hex[:8]}"
    second_clock = Clock()
    other = Memory.open(name, packs=("core", "people"), driver=driver, clock=second_clock, create=True)
    try:
        replay = ChatExtractor(Recording(tmp_path / "r.jsonl"))
        run(other, second_clock, replay)
        assert sorted(c.id for c in other.all_claims()) == sorted(c.id for c in memory.all_claims())
        assert sorted(s.candidate.id for s in store.pending(other)) == sorted(s.candidate.id for s in store.pending(memory))
        assert replay.tally.decisions == first.tally.decisions
        assert replay.tally.calls == 0 and replay.tally.replayed == 6 and replay.tally.charged_microusd == 0
    finally:
        driver.databases.get(name).delete()


def test_rerunning_records_no_second_decision(memory, clock, ledger, tmp_path):
    run(memory, clock, live(tmp_path, ledger))
    before = [len(s.decisions) for s in store.pending(memory)]
    run(memory, clock, ChatExtractor(Recording(tmp_path / "r.jsonl")))
    assert [len(s.decisions) for s in store.pending(memory)] == before
    assert ledger.spent_microusd() == 6 * 285


def test_the_ledger_cap_stops_the_run_before_it_is_exceeded(memory, clock, driver, tmp_path):
    name = f"gupi-test-ledger-{uuid.uuid4().hex[:8]}"
    tight = Ledger(driver, name, limit_usd=0.01, run_cap_usd=0.0025, clock=Clock())
    try:
        transport = Scripted()
        e = ChatExtractor(Recording(tmp_path / "r.jsonl"), transport, tight, Limits(max_calls=20))
        with pytest.raises(chat.RunStopped):
            run(memory, clock, e)
        assert transport.calls < len(TURNS) and tight.spent_microusd() <= 2500
        assert len(e.recording.entries) == transport.calls       # what was paid for stays recorded
    finally:
        driver.databases.get(name).delete()
