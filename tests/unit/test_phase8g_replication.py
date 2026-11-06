"""The 8G additions on invented ledgers, and proof that the 8F method is untouched."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from gupi.benchmarks import phase8f_agreement as f
from gupi.benchmarks import phase8g_replication as g

ROOT = Path(__file__).resolve().parents[2]
TEXT = {"D1:1": "I started learning to sail last spring.", "D2:1": "I sail on Sundays.", "D3:1": "I stopped sailing.", "D3:2": "I bought a kiln."}
WHO = {k: "Juno" for k in TEXT}
SAID = {k: datetime(2024, i + 1, 1, tzinfo=UTC) for i, k in enumerate(TEXT)}
AFTER = max(SAID.values()) + timedelta(days=1)


def m(turn, quote, role="engagement", link="clear", time=None):
    return {"turn": turn, "quote": quote, "role": role, "link": link, "time": time}


def act(i, state, *mentions):
    return {"id": i, "person": "Juno", "label": "secret label", "basis": "explicit", "final_state": state, "mentions": list(mentions)}


SAIL = [m("D1:1", "I started learning to sail", "start"), m("D2:1", "I sail on Sundays"), m("D3:1", "I stopped sailing", "end")]


def test_frozen_files_are_unchanged():
    frozen = json.loads((ROOT / "benchmarks/phase8g.json").read_text())["frozen_sha256"]
    assert len(frozen) == 7
    for path, digest in frozen.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path


def test_verdict_reproduces_the_8f_verdict_from_the_8f_numbers():
    numbers = json.loads((ROOT / "docs/evaluation/phase-8f/results/8f-agreement.json").read_text())
    thresholds = json.loads((ROOT / "benchmarks/phase8f.json").read_text())["thresholds"]
    v = g.verdict(numbers, thresholds)
    assert v["passed"] == {"1_reproducible": False, "2_merges_continuity": False, "3_provenance": True, "4_temporal_ambiguity": True, "5_automation": False}
    assert v["criteria"]["1_reproducible"] == {"mention_f1": True, "activity_f1": False, "adjusted_rand": False, "bcubed_f1": True}
    assert v["criteria"]["5_automation"]["automated_reaches_readers"] and v["automated_reaching_readers"] == ["C1"]


def test_cases_hide_label_state_role_and_source():
    cases, key = g.build_cases({"A": {"activities": [act("x", "ended", *SAIL)]}, "B": {"activities": [act("y", "unknown", SAIL[0])]}})
    text = json.dumps(cases)
    assert "secret label" not in text and "ended" not in text and "start" not in text.replace("started", "") and '"A"' not in text
    assert sorted(map(tuple, key.values())) == [("A", "x"), ("B", "y")] and set(cases[0]) == {"case", "person", "evidence"}


def test_reference_keeps_only_what_both_judges_agree():
    key = {"c1": ["A", "x"], "c2": ["A", "y"], "c3": ["B", "z"]}
    one = {"judgements": [{"case": "c1", "state": "ended"}, {"case": "c2", "state": "unknown"}, {"case": "c3", "state": "not a state"}]}
    two = {"judgements": [{"case": "c1", "state": "ended"}, {"case": "c2", "state": "engaged"}, {"case": "c3", "state": "not a state"}]}
    assert g.reference(one, two, key) == {("A", "x"): "ended"}


def test_computed_states_use_the_classifier_and_ignore_what_the_reader_wrote():
    ledger = {"activities": [act("a", "engaged", *SAIL), act("b", "engaged", m("D2:1", "I sail on Sundays"))]}
    states = g.computed(ledger, SAID, WHO, AFTER)
    assert states["a"][0] == "ended" and "D3:1" in states["a"][1]
    assert states["b"][0] == "unknown"
    assert g.computed(ledger, SAID, WHO, SAID["D2:1"])["b"][0] == "engaged"          # a statement holds at its own moment


def test_presumed_reads_as_unknown_because_engaged_needs_direct_evidence():
    assert g.mapped("presumed") == "unknown" and g.mapped("confirmed") == "engaged" and g.mapped("ended") == "ended"


def test_accuracy_separates_unsafe_wrong_way_and_missed():
    ledger = {"activities": [act("a", "engaged", SAIL[1]), act("b", "ended", SAIL[1]), act("c", "unknown", SAIL[1]), act("d", "engaged", SAIL[1])]}
    ref = {("A", "a"): "unknown", ("A", "b"): "engaged", ("A", "c"): "ended", ("A", "d"): "not_one_activity"}
    states = {k: ("unknown", ()) for k in "abcd"}
    r = g.accuracy(ledger, "A", ref, states, states)
    assert r["written"] == {"n": 3, "correct": 0, "unsafe": 1, "wrong_way": 1, "missed": 1}
    assert r["computed"]["correct"] == 1 and r["not_one_activity"] == 1 and r["decided"] == 4


def test_a_gain_by_two_empty_unknowns_is_not_called_genuine():
    x, y = {"activities": [act("a", "engaged", SAIL[1], SAIL[0])]}, {"activities": [act("b", "unknown", SAIL[1], SAIL[0])]}
    ref = {("A", "a"): "unknown", ("B", "b"): "unknown"}
    r = g.decompose(x, y, ("A", "B"), ref, {"a": ("unknown", ())}, {"b": ("unknown", ())}, TEXT, WHO)
    assert r["gained"] == 1 and r["gained_correct_by_default"] == 1
    r = g.decompose(x, y, ("A", "B"), {("A", "a"): "ended", ("B", "b"): "ended"}, {"a": ("ended", ("D3:1",))}, {"b": ("ended", ("D3:1",))}, TEXT, WHO)
    assert r["gained_correct_same_evidence"] == 1
    r = g.decompose(x, y, ("A", "B"), {}, {"a": ("ended", ("D3:1",))}, {"b": ("ended", ("D3:1",))}, TEXT, WHO)
    assert r["gained_undecided"] == 1


def test_burden_counts_everything_a_reviewer_must_see():
    ledger = {"activities": [{}, {"basis": "inferred"}], "not_same": [{}], "contradictions": [{}], "review": [{}, {}]}
    assert g.burden(ledger, 50) == {"activities": 2, "not_same": 1, "contradictions": 1, "review": 2, "items": 6, "per_100_turns": 12.0, "inferred": 1}


def test_contradictions_cluster_by_shared_turns_across_ledgers():
    ledgers = {"A": {"contradictions": [{"turns": ["D1:1", "D2:1"]}]}, "B": {"contradictions": [{"turns": ["D2:1"]}, {"turns": ["D3:1"]}]}}
    assert g.contradiction_clusters(ledgers) == {"reports": 3, "distinct": 2, "by_number_of_ledgers": {"1": 1, "2": 1}}


def test_the_scorer_is_called_not_copied():
    assert g.f is f and not hasattr(g, "adjusted_rand")
