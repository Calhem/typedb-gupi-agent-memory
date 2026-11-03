"""The 6B scorer: matching, precision and recall kept apart, and correct rejections not counted as extractions."""

from gupi import ids
from gupi.formation import evaluation
from gupi.formation.candidate import Candidate, CandidateSet, Participant, Passage, TimeEvidence

DATA = {"observed_at": "2025-08-20T09:00:00Z", "passages": [
    {"id": "a", "text": "Ann Lee joined Acme in May 2025.",
     "expect": [{"type": "employment", "roles": {"employee": "Ann Lee", "employer": "Acme"}, "times": [["start", "May 2025"]]}]},
    {"id": "b", "text": "Acme is hiring.", "expect": []},
    {"id": "c", "text": "Ann Lee reports to Bo Kim.", "expect": [{"type": "reporting", "roles": {"report": "Ann Lee", "manager": "Bo Kim"}}]},
]}


def cand(text, claim_type, roles, times=()):
    parts = tuple(Participant(r, s, text.index(s), text.index(s) + len(s), "person") for r, s in roles.items())
    return Candidate(claim_type, Passage("obs:x", 0, len(text), text), parts, (), tuple(times))


def cset(*cs):
    return CandidateSet("obs:x", ids.content_hash("x"), "test:v1", tuple(cs))


def test_precision_recall_fields_and_correct_rejections():
    a = DATA["passages"][0]["text"]
    outputs = {
        "a": cset(cand(a, "employment", {"employee": "Ann Lee", "employer": "Acme"},
                       [TimeEvidence("holds-since", "May 2025", 22, 30, None, None)])),   # matched, wrong time kind
        "b": cset(),                                                                       # correct rejection
        "c": cset(cand("Ann Lee reports to Bo Kim.", "reporting", {"report": "Bo Kim", "manager": "Ann Lee"})),  # swapped
    }
    r = evaluation.score(DATA, outputs)
    assert (r["extracted"], r["expected"], r["matched"]) == (2, 2, 1)
    assert (r["precision"], r["recall"], r["correct_rejections"], r["empty_passages"]) == (0.5, 0.5, 1, 1)
    assert r["fields"]["times"] == {"correct": 0, "of": 1} and r["fields"]["modality"] == {"correct": 1, "of": 1}


def test_frozen_set_is_well_formed():
    data = evaluation.load()
    ids_ = [p["id"] for p in data["passages"]]
    assert len(ids_) == len(set(ids_)) == 32 and data["frozen"] == "2026-11-03"
    for p, obs in evaluation.observations(data):
        for e in p["expect"]:
            for role, surface in e["roles"].items():
                assert surface in p["text"] or surface in ("He", "I"), (p["id"], surface)
