from datetime import datetime, timezone
from types import SimpleNamespace as NS

from gupi.conflicts import CONTRADICTION, CORROBORATION, DIFFERING, SEPARATE, compare, detect
from gupi.temporal import ValidTime

RULES = {"single_valued_attributes": {"employment": ["job-title"]},
         "one_player_at_a_time": {"reporting": {"per": "report", "single": "manager"}}}


def d(y, m=1):
    return datetime(y, m, 1, tzinfo=timezone.utc)


def claim(cid, valid, values=None, ctype="employment", key="prop:1", roles=None):
    return NS(id=cid, type=ctype, proposition_key=key, values=values or {}, valid=valid,
              roles=roles or {"employee": ("p:a",), "employer": ("o:x",)})


SINCE_JUNE_ONGOING = ValidTime(d(2025, 6), d(2025, 7), to_earliest=d(2025, 10))


def test_same_period_opposite_certainty_is_a_contradiction():
    ended = claim("a", ValidTime(d(2024, 3), d(2024, 4), d(2025, 6), d(2025, 7)))
    still = claim("b", ValidTime(d(2024, 3), d(2024, 4), to_earliest=d(2025, 9)))
    c = compare(ended, still, RULES)
    assert c.kind == CONTRADICTION and c.period == (d(2025, 7), d(2025, 9))


def test_two_spells_are_separate_periods_not_a_contradiction():
    first = claim("a", ValidTime(d(2020), d(2020), d(2021), d(2021)))
    second = claim("b", ValidTime(d(2024), d(2024), to_earliest=d(2025)))
    assert compare(first, second, RULES).kind == SEPARATE


def test_single_valued_attribute_both_certain_at_once_is_a_contradiction():
    cto = claim("a", SINCE_JUNE_ONGOING, {"job-title": "CTO"})
    vp = claim("b", SINCE_JUNE_ONGOING, {"job-title": "VP Engineering"})
    assert compare(cto, vp, RULES).kind == CONTRADICTION


def test_values_that_may_be_sequential_are_differing_evidence():
    senior = claim("a", ValidTime(to_earliest=d(2025, 2)), {"job-title": "Senior Engineer"})  # start unknown
    staff = claim("b", ValidTime(to_earliest=d(2025, 9)), {"job-title": "Staff Engineer"})
    c = compare(senior, staff, RULES)
    assert c.kind == DIFFERING and "possibly sequential" in c.reason


def test_corroboration_and_compatible_detail():
    assert compare(claim("a", SINCE_JUNE_ONGOING), claim("b", SINCE_JUNE_ONGOING), RULES).kind == CORROBORATION
    vaguer = claim("b", ValidTime(d(2025), d(2026), to_earliest=d(2025, 10)))  # "since 2025"
    assert compare(claim("a", SINCE_JUNE_ONGOING), vaguer, RULES).kind == DIFFERING


def test_one_manager_at_a_time_across_propositions():
    def rep(cid, manager, valid):
        return claim(cid, valid, ctype="reporting", key=f"prop:{manager}",
                     roles={"report": ("p:a",), "manager": (manager,)})
    bob = rep("a", "p:bob", ValidTime(d(2024), d(2024), to_earliest=d(2025, 6)))
    sam = rep("b", "p:sam", ValidTime(d(2025, 3), d(2025, 3), to_earliest=d(2025, 9)))
    later = rep("c", "p:dana", ValidTime(d(2025, 7), d(2025, 7), to_earliest=d(2025, 9)))
    kinds = {(x.claim_ids, x.kind) for x in detect([bob, sam, later], RULES)}
    assert (("a", "b"), CONTRADICTION) in kinds          # Bob and Sam overlap March-June
    assert not any(ids == ("a", "c") for ids, _ in kinds)  # Bob then Dana: sequential, fine
