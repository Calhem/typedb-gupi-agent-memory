"""Answer semantics v2 against the live server: belief-time history, corrections, negation and provenance.

The scenario replays truth-table rows R9-R12′ (docs/specialist/v2-truth-semantics.md §4) through TypeDB's
own belief cutoff: a late termination, a correction recorded as a supersession, and as-of questions.
"""

import pytest
from helpers import CHAT, HR, month, observe, record, reports, utc

from gupi.query import Question
from gupi.temporal import Answer, ValidTime

pytestmark = pytest.mark.integration

ROLES = {"report": "p:alice", "manager": "p:bob"}


@pytest.fixture
def history(memory, clock):
    joined = observe(HR, "hr-1", "Alice started reporting to Bob in January 2024.", "2024-01-21")
    chat = observe(CHAT, "c-1", "Alice still reports to Bob.", "2024-07-01")
    left = observe(HR, "hr-2", "Alice stopped reporting to Bob in March 2024.", "2024-09-01")
    fix = observe(HR, "hr-3", "Correction: she stopped in February, not March.", "2024-10-01")
    j1 = reports(joined, valid=ValidTime(*month("2024-01")))
    ch = reports(chat, valid=ValidTime(to_earliest=utc("2024-07-01")), valid_to_basis="ongoing-at-observation")
    l1 = reports(left, valid=ValidTime(to_earliest=month("2024-03")[0], to_latest=month("2024-03")[1]))
    k = reports(fix, valid=ValidTime(to_earliest=month("2024-02")[0], to_latest=month("2024-02")[1]))
    for when, obs, c in (("2024-01-21", joined, j1), ("2024-07-01", chat, ch), ("2024-09-01", left, l1),
                         ("2024-10-01", fix, k)):
        clock.set(when)
        record(memory, [obs], [c])
        memory.review(c.id, "accepted", "reviewer")
    memory.supersede(l1.id, k.id, reason="corrected month", decided_by="reviewer")
    clock.set("2025-01-01")
    return {"J1": j1, "CHAT": ch, "L1": l1, "K": k}


def ask(memory, valid, believed, semantics="v2"):
    return memory.ask("reporting", ROLES, utc(valid), believed_at=utc(believed), semantics=semantics)


def deciding(result, history):
    names = {c.id: n for n, c in history.items()}
    return sorted(names[c.id] for c, _ in result.believed)


def test_v2_follows_belief_time_history(memory, history):
    cases = [  # (valid, believed, answer, basis, deciding claims): rows R9, R10, R11, R11b, R12, R12′
        ("2024-07-01", "2024-08-01", Answer.TRUE, "direct-point", ["CHAT"]),
        ("2024-05-01", "2024-08-01", Answer.PRESUMED, "joined-spell", ["CHAT", "J1"]),
        ("2024-05-01", "2024-09-15", Answer.FALSE, "termination-continuing", ["L1"]),
        ("2024-07-01", "2024-09-15", Answer.CONTESTED, "conflict", ["CHAT", "L1"]),
        ("2024-02-20", "2024-10-15", Answer.UNKNOWN, "window", ["K"]),
        ("2024-02-20", "2024-09-15", Answer.PRESUMED, "joined-spell", ["J1", "L1"]),
    ]
    for valid, believed, answer, basis, claims in cases:
        r = ask(memory, valid, believed)
        assert (r.answer, r.evaluation.basis.kind, deciding(r, history), r.semantics) == \
            (answer, basis, claims, "v2"), (valid, believed)
    assert ask(memory, "2024-05-01", "2023-12-01").answer is Answer.NOT_YET_KNOWN


def test_v1_is_unchanged_and_selected_by_default(memory, history):
    assert memory.ask("reporting", ROLES, utc("2024-05-01"), believed_at=utc("2024-08-01")).answer is Answer.TRUE
    assert ask(memory, "2024-05-01", "2024-08-01", semantics="v1").semantics == "v1"
    with pytest.raises(ValueError, match="semantics"):
        ask(memory, "2024-05-01", "2024-08-01", semantics="v3")


def test_v2_query_cites_the_deciding_evidence_and_explains_the_default(memory, history):
    r = memory.query(Question("reporting", ROLES, utc("2024-05-01"), utc("2024-09-15"), semantics="v2"))
    assert r.answer is Answer.FALSE and r.temporal["semantics"] == "v2"
    (cite,) = r.citations
    assert (cite.quote, cite.source_id, cite.verdict) == ("Alice stopped reporting to Bob in March 2024.", "src:hr", "ended")
    (b,) = r.bindings
    assert b.basis.kind == "termination-continuing" and "default, not an observation" in b.explanation


def test_v2_answers_an_explicit_negation_within_its_own_time_only(memory, clock):
    neg = observe(HR, "hr-n", "Alice does not report to Bob.", "2025-04-01")
    c = reports(neg, valid=ValidTime(to_earliest=utc("2025-04-01")), polarity="negative")
    clock.set("2025-04-02")
    record(memory, [neg], [c])
    memory.review(c.id, "accepted", "reviewer")
    r = memory.query(Question("reporting", ROLES, utc("2025-04-01"), semantics="v2"))
    assert r.answer is Answer.FALSE and r.bindings[0].basis.kind == "negation"
    assert [x.verdict for x in r.citations] == ["negative"]
    assert memory.ask("reporting", ROLES, utc("2025-05-01"), semantics="v2").answer is Answer.UNKNOWN
