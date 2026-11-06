"""The frozen selection rule, the control and the pre-registered comparison. No database, no dataset text."""

import json

import pytest

from gupi.benchmarks import phase8c_eval as ev

Q = {"question": "Where did they meet?", "category": 1, "evidence": ["D1:3", "D4:2"]}


def test_selection_uses_only_the_datasets_labels():
    assert ev.stratum(Q) == "multi-hop"
    assert ev.stratum(dict(Q, evidence=["D1:3", "D1:4"])) is None        # one session is not multi-session
    assert ev.stratum(dict(Q, evidence=["D1:3"])) is None
    assert ev.stratum(dict(Q, evidence=["D1:3", " D1:3"])) is None       # a repeat is one turn
    assert ev.stratum(dict(Q, category=2, evidence=["D1:3"])) == "temporal"
    assert ev.stratum(dict(Q, category=2, evidence=[])) is None
    assert ev.stratum(dict(Q, category=4)) is None


def test_frozen_items_hold_ids_and_hashes_only():
    item = ev.select({"sample_id": "conv-x", "qa": [Q]})[0]
    assert set(item) == {"id", "stratum", "question_sha256", "gold_turns"} and "meet" not in json.dumps(item)


def test_the_committed_set_is_large_enough_and_has_no_text():
    record = json.loads(ev.FROZEN.read_text())
    strata = [i["stratum"] for i in record["items"]]
    assert strata.count("multi-hop") >= 50 and strata.count("temporal") >= 30
    assert record["conversations"] == ["conv-41", "conv-42"]
    assert all(set(i) == {"id", "stratum", "question_sha256", "gold_turns"} for i in record["items"])


def test_a_frozen_set_is_never_rewritten(tmp_path):
    path = tmp_path / "f.json"
    path.write_text("{}")
    with pytest.raises(FileExistsError):
        ev.freeze(path)


PACK = {"format": ev.PACK_FORMAT, "author": "someone else", "author_saw_gupi": False,
        "sessions": [{"id": "s1", "turns": [{"id": "t1", "speaker": "A", "at": "2024-01-01", "text": "x"}]}],
        "questions": [{"id": "q1", "category": "identity", "question": "?", "answer": "a", "evidence": ["t1"]}]}


def test_an_independent_pack_must_say_who_wrote_it_and_cite_real_turns():
    assert not ev.check_pack(PACK)
    assert ev.check_pack(dict(PACK, author_saw_gupi=True))
    assert ev.check_pack(dict(PACK, format="other"))
    assert ev.check_pack(dict(PACK, questions=[dict(PACK["questions"][0], evidence=["t9"])]))
    assert ev.check_pack(dict(PACK, questions=[dict(PACK["questions"][0], category="other")]))
    assert ev.check_pack(dict(PACK, questions=PACK["questions"] * 2))


def test_the_control_ignores_sentence_openers_but_finds_names():
    words = ev.name_words({"a": "The trip to Oslo with Dana was long.", "b": "Yesterday we met.", "c": "Dana called."})
    assert words == {"Oslo", "Dana"}


def row(q, system, recall, ids=()):
    return {"question": q, "stratum": "multi-hop", "system": system, "seconds": .1, "ids": list(ids), "gold": ["g"],
            **{f"recall@{k}": recall for k in ev.KS}, **{f"complete@{k}": recall == 1 for k in ev.KS}}


def test_the_interval_is_repeatable_and_a_gain_needs_size_and_confidence():
    deltas = [.5, .25, 0, .25] * 10
    assert ev.paired(deltas) == ev.paired(deltas)
    assert ev.shown(ev.paired(deltas))
    assert not ev.shown(ev.paired([.02] * 40))           # certain but too small
    assert not ev.shown(ev.paired([1, -1, 0, 0]))        # large mean noise, interval crosses zero
    assert ev.paired([]) ["questions"] == 0


def test_the_decision_needs_c_to_beat_both_b_and_the_control():
    questions = [f"q{i}" for i in range(30)]
    rows = lambda d: [r for q in questions for r in (row(q, "C-claim-paths", 1, ["g"]), row(q, "B-conversational", .5),
                                                     row(q, "D-name-control", d), row(q, "A-keyword", .5),
                                                     row(q, "C+-unresolved-links", 1, ["g"]))]
    assert all(ev.summarise(rows(.5))["decision"].values())
    assert not any(ev.summarise(rows(1))["decision"].values())


def test_counts_only_gold_that_no_text_system_found():
    rows = [row("q", "C-claim-paths", 1, ["g"]), row("q", "B-conversational", 0, ["x"]), row("q", "D-name-control", 0, ["y"])]
    assert ev.only_claims_found(rows, 5) == 1
    rows[2]["ids"] = ["g"]
    assert ev.only_claims_found(rows, 5) == 0


def test_integrity_catches_each_must_be_zero_case():
    from gupi import paths
    item = paths.Item("o1", "accepted", ("keyword",), ("pending retraction: x",))
    hop = paths.Hop("c", "a", "b", (), "runs", "qualified", ("identity not confirmed: a and b may be different",))
    found = paths.EvidenceSet([item], [paths.Path((hop,), ("a", "b"), None, False)])
    bad = " | ".join(ev.integrity(found, frozenset()))
    for text in ("shown as accepted", "outside the question's scope", "hop with no evidence", "shown as firm"):
        assert text in bad
