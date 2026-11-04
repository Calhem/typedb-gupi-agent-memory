"""Phase 6D runner pieces that need no TypeDB: gold isolation, missing vs incorrect, matching, the probe."""

import re

from gupi.benchmarks.common import BenchQuestion
from gupi.benchmarks.e2e import common, conversational, formation_layer, scale, world
from gupi.formation.rules_v2 import NAME
from gupi.temporal import Answer

Q = [{"id": "x1", "text": "t", "type": "employment", "roles": {"employee": "A B", "employer": "C"}, "valid_at": "2025-01-01",
      "gold": {"answer": "TRUE", "evidence": ["m1"]}},
     {"id": "x2", "text": "t", "type": "employment", "roles": {"employee": None, "employer": "C"}, "valid_at": "2025-01-01",
      "believed_at": "2025-02-01", "gold": {"answer": "UNKNOWN"}},
     {"id": "x3", "text": "t", "type": "employment", "roles": {"employee": "A B", "employer": "C"}, "valid_at": "2025-01-01",
      "gold": {"answer": "CONTESTED", "evidence": ["m1", "m2"]}}]
KEY_OF = {"o1": "m1", "o2": "m2"}


def out(answer, obs=(), standing="direct", error=None):
    return {"answer": answer, "binding": [], "observations": list(obs), "seconds": 0.01, "standing": standing,
            "error": error}


def test_public_never_carries_gold():
    p = common.public(Q[0])
    assert "gold" not in p and p["roles"] == Q[0]["roles"] and "gold" in Q[0]


def test_missing_is_not_incorrect_and_not_an_assertion():
    s = world.score(Q, {"x1": out(Answer.TRUE, ["o1"]), "x2": out(None, error="boom"), "x3": out(Answer.TRUE, ["o1"])}, KEY_OF)
    assert (s["correct"], s["missing"], s["incorrect"]) == (1, 1, 1)
    assert s["unsupported_definitive"] == 1          # x3: TRUE where the gold is CONTESTED; x2 missing is not counted
    assert s["by_category"]["contradiction"] == {"correct": 0, "of": 1}
    assert s["by_category"]["belief-time"] == {"correct": 0, "of": 1}


def test_definitive_on_qualified_evidence_is_unsupported():
    s = world.score(Q[:1], {"x1": out(Answer.TRUE, ["o1"], standing="qualified")}, KEY_OF)
    assert s["correct"] == 1 and s["unsupported_definitive_parts"] == {
        "definitive_where_gold_abstains_or_contested": 0, "definitive_on_evidence_not_direct": 1}


def test_categories_come_from_question_fields():
    assert world.categories(Q[1]) == ["temporal-status", "abstention", "belief-time", "open-role"]


def test_matching_is_one_to_one_and_case_insensitive():
    cands = [{"type": "reporting", "roles": {"report": "kim", "manager": "Noah"}}]
    gold = [{"type": "reporting", "roles": {"report": "Kim", "manager": "Noah"}}] * 2
    pairs, misses, extra = formation_layer._match(cands, gold)
    assert (len(pairs), len(misses), extra) == (1, 1, [])


def test_precision_at_5_uses_the_gold_count():
    q = BenchQuestion("q", "t", "c", [], None, {"turn": {"a", "b"}})
    (r,) = conversational._with_precision([{"question": "q", "unit": "turn", "recall@5": 0.5}], [q])
    assert r["precision@5"] == 0.2


def test_scale_names_are_distinct_and_extractable():
    a, b = scale.rename("Mara Quist joined Pellwick.", 0), scale.rename("Mara Quist joined Pellwick.", 1)
    assert a != b and a.endswith(".")
    assert re.fullmatch(NAME, a.split(" joined ")[0]) and "Pellwick" in a
