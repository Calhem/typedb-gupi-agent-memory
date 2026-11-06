"""The Phase 8C runner on an invented conversation in LoCoMo's shape: replay only, no model, no dataset."""

import argparse
import json
from collections import Counter
from types import SimpleNamespace

import pytest

from gupi.benchmarks import locomo, phase8c
from gupi.formation import chat_extractor as chat
from gupi.formation.chat_extractor import ChatExtractor, Limits, Recording
from gupi.formation.model_candidate import RESPONSE_FORMAT

pytestmark = pytest.mark.integration
SAMPLE = {"sample_id": "conv-x", "qa": [], "conversation": {
    "speaker_a": "Juno", "speaker_b": "Bram",
    "session_1_date_time": "1:56 pm on 8 May, 2023",
    "session_1": [{"speaker": "Juno", "dia_id": "D1:1", "text": "Dana Voss joined Fenwick Labs in 2021."},
                  {"speaker": "Bram", "dia_id": "D1:2", "text": "Good to hear!"}],
    "session_2_date_time": "2:00 pm on 9 June, 2023",
    "session_2": [{"speaker": "Juno", "dia_id": "D2:1", "text": "I adopted a greyhound."}]}}


def person(role, text, kind="person"):
    return {"role": role, "text": text, "kind": kind, "is_pronoun_or_vague": False}


BASE = {"evidence_occurrence": None, "polarity": "positive", "modality": "actual", "commitment": "certain", "basis": "explicit",
        "attribution": {"mode": "direct", "claimant": None, "claimant_kind": None, "via": []}, "object_text": None, "title": None,
        "allegation": None, "correction": None}
REPLIES = {
    "D1:1": [BASE | {"evidence": "Dana Voss joined Fenwick Labs in 2021", "relation": "employment", "predicate": None,
                     "participants": [person("employee", "Dana Voss"), person("employer", "Fenwick Labs", "organization")],
                     "times": [{"text": "2021", "kind": "start"}]}],
    "D1:2": [],
    "D2:1": [BASE | {"evidence": "I adopted a greyhound", "relation": "statement", "predicate": "adopted", "object_text": "a greyhound",
                     "participants": [person("subject", "I")], "times": []}]}


def recorded(tmp_path, turns=None):
    """A recording with one reply per turn, as a finished live run would leave it."""
    recording = Recording(tmp_path / "r.jsonl")
    for o, author, before in phase8c.requests(SAMPLE, turns):
        body = chat.build_request(o, author, before)
        turn = o.record_key.split(":", 1)[1]
        text = json.dumps({"format": RESPONSE_FORMAT, "outcome": "assertions" if REPLIES[turn] else "no-relevant-assertion",
                           "assertions": REPLIES[turn], "problems": []})
        recording.add({"key": chat.request_key(body), "observation": o.id, "reply": {"model": "gpt-4o-mini-2024-07-18", "choices": [
            {"finish_reason": "stop", "message": {"content": text}}], "usage": {"prompt_tokens": 1900, "completion_tokens": 120}}})
    return recording


def test_requests_match_the_observations_the_benchmark_ingests(memory, clock):
    turn_ids, _ = locomo.ingest(memory, clock, [SAMPLE])
    assert {o.id for o, _, _ in phase8c.requests(SAMPLE)} == set(turn_ids.values())


def test_a_replayed_conversation_reports_each_stage_separately(memory, clock, tmp_path):
    e = ChatExtractor(recorded(tmp_path))
    observations, stopped = phase8c.build(memory, clock, [SAMPLE], e)
    assert stopped is None and len(observations) == 3
    assert e.tally.calls == 0 and e.tally.replayed == 3 and not e.tally.failures
    assert e.tally.decisions == {"formed": 2} and e.tally.outcomes["no-relevant-assertion"] == 1
    graph = phase8c.graph_report(memory, observations, {observations[0].id, observations[1].id})
    assert (graph["claims"], graph["linking_claims"]) == (2, 1)
    assert graph["turns_with_a_claim"] == 2 and graph["gold_turns_with_a_claim"] == 1
    assert graph["claims_reaching_another_session"] == 0


def test_an_incomplete_recording_stops_nothing_silently(memory, clock, tmp_path):
    e = ChatExtractor(recorded(tmp_path, turns=2))
    observations, _ = phase8c.build(memory, clock, [SAMPLE], e)
    assert e.tally.failures["no-recording"] == 1 and len(observations) == 3


def test_a_limit_ends_the_run_cleanly_and_says_why(memory, clock, tmp_path):
    class Ledger:
        def reserve(self, *a, **k):
            return "c", 1

        def settle(self, *a):
            return 1

        def fail(self, *a):
            pass
    recording = Recording(tmp_path / "empty.jsonl")
    transport = lambda body: {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(
        {"format": RESPONSE_FORMAT, "outcome": "no-relevant-assertion", "assertions": [], "problems": []})}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1}, "model": "gpt-4o-mini"}
    e = ChatExtractor(recording, transport, Ledger(), Limits(max_calls=2))
    observations, stopped = phase8c.build(memory, clock, [SAMPLE], e)
    assert "limit of 2 calls" in stopped and len(observations) == 2


def args(tmp, **over):
    return argparse.Namespace(**({"recording": str(phase8c.DATA / "phase8c" / "r.jsonl"), "live": False, "approved_cap_usd": None,
                                  "approved_frozen_run": False, "gate": "smoke"} | over))


def test_guards_refuse_every_unapproved_live_run(tmp_path):
    gate = phase8c.CONFIG["gates"]["smoke"]
    assert not phase8c.guard(args(tmp_path), gate)
    assert "must be inside .data" in phase8c.guard(args(tmp_path, recording=str(tmp_path / "r.jsonl")), gate)[0]
    assert "needs --approved-cap-usd" in phase8c.guard(args(tmp_path, live=True), gate)[0]
    assert "may not exceed" in phase8c.guard(args(tmp_path, live=True, approved_cap_usd=5.0), gate)[0]
    frozen = phase8c.CONFIG["gates"]["frozen"]
    assert "--approved-frozen-run" in phase8c.guard(args(tmp_path, live=True, approved_cap_usd=1.0, gate="frozen"), frozen)[0]
    assert not phase8c.guard(args(tmp_path, live=True, approved_cap_usd=1.0, gate="frozen", approved_frozen_run=True), frozen)


def test_readiness_is_a_frozen_rule():
    good = SimpleNamespace(outcomes=Counter({"grounding-failure": 2}), candidates=18, decisions=Counter(formed=9))
    assert phase8c.readiness(good, {"linking_share": .2})["go"]
    assert not phase8c.readiness(good, {"linking_share": .05})["go"]
    bad = SimpleNamespace(outcomes=Counter({"grounding-failure": 9}), candidates=11, decisions=Counter(formed=5))
    assert "unusable" in phase8c.readiness(bad, {"linking_share": .5})["problems"][0]
    none = SimpleNamespace(outcomes=Counter(), candidates=4, decisions=Counter(review=4))
    assert "no claim" in phase8c.readiness(none, {"linking_share": .5})["problems"][0]




def test_every_system_runs_on_the_same_question_and_scope(memory, clock, tmp_path):
    from gupi.benchmarks import common, phase8c_eval as ev
    e = ChatExtractor(recorded(tmp_path))
    observations, _ = phase8c.build(memory, clock, [SAMPLE], e)
    clock.now = clock.now.replace(year=clock.now.year + 1)
    gold = {observations[0].id}
    contexts = sorted({o.context_id for o in observations})
    q = common.BenchQuestion("q", "Who joined Fenwick Labs?", "multi-hop", contexts, clock.now, {"turn": gold})
    rows = ev.evaluate(memory, [q], {o.id: o.content for o in observations})
    assert {r["system"] for r in rows} == set(ev.SYSTEMS)
    for r in rows:
        assert set(r["ids"]) <= {o.id for o in observations} and r["recall@100"] == 1.0
    assert not ev.summarise(rows)["severe"]


def test_the_adjudication_sample_is_repeatable_and_counts_claims(memory, clock, tmp_path):
    from gupi.benchmarks import phase8c_eval as ev
    phase8c.build(memory, clock, [SAMPLE], ChatExtractor(recorded(tmp_path)))
    first = ev.adjudication_sample(memory, 1)
    assert first == ev.adjudication_sample(memory, 1) and len(ev.adjudication_sample(memory, 10)) == 2
    assert {"claim", "quote", "commitment", "attribution"} <= set(first[0])
