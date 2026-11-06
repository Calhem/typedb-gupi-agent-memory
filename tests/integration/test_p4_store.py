"""P4 on a live TypeDB: events through the protected pipeline, with temporal and integrity regressions."""

from datetime import datetime, timezone

import pytest

from gupi import paths
from gupi.benchmarks import phase8_paths as runner
from gupi.formation import store
from gupi.formation.candidate import EVENT_TYPE
from gupi.memory import Memory
from gupi.query import Question
from gupi.temporal import Answer

pytestmark = pytest.mark.integration
P, O, U = "person", "organization", "unclassified"


def ev(pred, s, *t, o=None, sk=P, ok=U, **k):
    parts = [["subject", s, sk]] + ([["object", o, ok]] if o else [])
    return dict(rel="event", p=parts, t=[[x, "holds-at"] for x in t], pred=pred, **k)


def emp(n, o, *t, **k):
    return dict(rel="employment", p=[["employee", n, P], ["employer", o, O]], t=[list(x) for x in t], **k)


def msg(key, day, text, *a, ctx="s1", author="Ada Finch"):
    return dict(key=key, context=ctx, at=f"{day}T09:00:00Z", author=author, text=text, assertions=list(a))


@pytest.fixture
def build(driver, database):
    def _build(*messages):
        clock = runner.Clock()
        memory = Memory.open(database, packs=("core", "people"), driver=driver, clock=clock)
        keys, statuses = runner.build(memory, clock, dict(messages=list(messages), identity=dict(never_merge=[])))
        return memory, keys, statuses, clock
    return _build


def utc(y, m=6):
    return datetime(y, m, 1, tzinfo=timezone.utc)


def event(memory):
    return next(c for c in memory.all_claims() if c.type == EVENT_TYPE)


def subject(claim):
    return claim.roles["subject"][0]


MOVED = msg("m", "2024-03-01", "Kate Reed moved to Bristol in 2021.", ev("moved to", "Kate Reed", "2021", o="Bristol"))


def test_event_time_is_not_assertion_time(build):
    memory, keys, statuses, _ = build(MOVED)
    assert [s for _, s in statuses] == ["formed"]
    c = event(memory)
    assert c.occurred == (utc(2021, 1), utc(2022, 1)) and c.time_precision == "year"
    assert c.valid.from_earliest is None and c.valid.to_earliest is None and c.valid_to_basis is None
    (o,) = memory.events(subject(c))
    assert o.what == "moved to" and (o.earliest.year, o.basis) == (2021, "stated") and o.said_at.year == 2024
    assert c.evidence[0].observation_id == keys["m"]


def test_a_derived_date_says_so(build):
    memory, _, _, _ = build(msg("m", "2024-03-20", "Kate Reed moved to Bristol last week.", ev("moved to", "Kate Reed", "last week", o="Bristol")))
    (o,) = memory.events(subject(event(memory)))
    assert o.basis == "derived" and o.earliest < o.latest <= utc(2024, 3).replace(day=21)


def test_a_missing_date_stays_missing(build):
    memory, _, _, _ = build(msg("m", "2024-03-20", "Kate Reed moved to Bristol.", ev("moved to", "Kate Reed", o="Bristol")))
    (o,) = memory.events(subject(event(memory)))
    assert o.earliest is None and o.latest is None and o.basis is None and o.said_at.year == 2024


def test_asking_whether_an_event_held_is_refused(build):
    memory, _, _, _ = build(MOVED)
    c = event(memory)
    with pytest.raises(ValueError, match="no holding period"):
        memory.ask(EVENT_TYPE, {"subject": subject(c)}, utc(2022))
    with pytest.raises(ValueError, match="no holding period"):
        memory.query(Question(EVENT_TYPE, {"subject": subject(c)}, utc(2022)))


def test_joining_as_an_event_implies_no_continuing_employment(build):
    memory, _, _, _ = build(msg("j", "2024-03-01", "Mina Roth joined Arbor Mills in 2020.", ev("joined", "Mina Roth", "2020", o="Arbor Mills", ok=O)))
    c = event(memory)
    roles = {"employee": subject(c), "employer": c.roles["object"][0]}
    for year in (2020, 2021, 2030):
        assert memory.ask("employment", roles, utc(year), semantics="v2").answer not in (Answer.TRUE, Answer.PRESUMED)


JOIN = msg("j", "2023-02-01", "Mina Roth joined Arbor Mills in 2019.", emp("Mina Roth", "Arbor Mills", ("2019", "start")))
LEFT = msg("l", "2023-02-02", "Mina Roth left Arbor Mills in 2021.", emp("Mina Roth", "Arbor Mills", ("2021", "end")))


def test_events_leave_spells_exactly_as_they_were(build):
    plain = [JOIN, LEFT]
    memory, _, _, _ = build(*plain, msg("e", "2023-02-03", "Mina Roth moved to Bristol in 2020.", ev("moved to", "Mina Roth", "2020", o="Bristol")),
                            msg("f", "2023-02-04", "Arbor Mills bought Sefton Mill in 2020.", ev("bought", "Arbor Mills", "2020", o="Sefton Mill", sk=O, ok=O)))
    c = next(x for x in memory.all_claims() if x.type == "employment")
    roles = {k: v[0] for k, v in c.roles.items()}
    ask = lambda y: memory.query(Question("employment", roles, utc(y), semantics="v2")).answer
    assert (ask(2020), ask(2022)) == (Answer.PRESUMED, Answer.FALSE)


def test_a_state_can_be_asked_about_an_events_time_but_not_the_reverse(build):
    memory, _, _, _ = build(JOIN, LEFT, msg("e", "2023-02-05", "Arbor Mills bought Sefton Mill in 2020.",
                                            ev("bought", "Arbor Mills", "2020", o="Sefton Mill", sk=O, ok=O)))
    views = memory.all_claims()
    state = [c for c in views if c.type == "employment"]
    happened = [c for c in views if c.type == EVENT_TYPE]
    assert paths.overlap_label(state, happened) == "presumed"
    assert paths._held_during(happened, state) is None


def test_two_events_have_no_overlap_to_claim(build):
    memory, _, _, _ = build(MOVED, msg("n", "2024-03-02", "Kate Reed bought a boat in 2021.", ev("bought", "Kate Reed", "2021", obj_text="a boat")))
    claims = [[c] for c in memory.all_claims() if c.type == EVENT_TYPE]
    assert paths.overlap_label(*claims) == "unknown"


def test_an_acquisition_links_two_organisations_and_stays_qualified_on_a_path(build):
    memory, _, _, _ = build(JOIN, msg("e", "2023-02-05", "Arbor Mills bought Sefton Mill in 2020.", ev("bought", "Arbor Mills", "2020", o="Sefton Mill", sk=O, ok=O)))
    found = paths.retrieve(memory, "Did Mina Roth work at Sefton Mill?", ["s1"], paths.Budget(k=10))
    chain = [p for p in found.paths if p.labels == ("Mina Roth", "Arbor Mills", "Sefton Mill")]
    assert chain and chain[0].overlap == "unknown"           # no recorded end: connected, and still not confirmed


def test_disputed_dates_are_both_kept_and_flagged(build):
    memory, _, _, _ = build(MOVED, msg("n", "2024-04-01", "Kate Reed moved to Bristol in 2022.", ev("moved to", "Kate Reed", "2022", o="Bristol")))
    found = memory.events(subject(event(memory)))
    assert len(found) == 2 and all(o.disputed for o in found) and [o.earliest.year for o in found] == [2021, 2022]
    hit = paths.retrieve(memory, "When did Kate Reed move to Bristol?", ["s1"], paths.Budget(k=10))
    assert any("sources disagree on the date" in n for p in hit.paths for h in p.hops for n in h.notes)


def test_a_correction_waits_for_review_and_then_replaces_the_date_with_history_intact(build):
    fixed = msg("n", "2024-04-01", "Correction: Kate Reed moved to Bristol in 2022.",
                ev("moved to", "Kate Reed", "2022", o="Bristol", corr=("corrects", "Correction"), commitment="certain"))
    memory, _, _, clock = build(MOVED, fixed)
    pending = store.pending(memory)
    assert len(pending) == 1 and pending[0].candidate.relations[0].kind == "corrects"
    original = event(memory)
    assert [o.earliest.year for o in memory.events(subject(original))] == [2021]
    before = clock.now
    clock.now = clock.now.replace(year=2030)
    store.review(memory, pending[0].candidate.id, "approve", "human-reviewer")
    new = store.get(memory, pending[0].candidate.id).claim_id
    clock.now = clock.now.replace(year=2031)
    memory.supersede(original.id, new, reason="a stated correction", decided_by="human-reviewer")
    assert [o.earliest.year for o in memory.events(subject(original))] == [2022]
    assert [o.earliest.year for o in memory.events(subject(original), believed_at=before)] == [2021]


def test_a_rejected_event_is_no_longer_believed(build):
    memory, _, _, clock = build(MOVED)
    c = event(memory)
    clock.now = clock.now.replace(year=2030)
    memory.review(c.id, "retracted", "human-reviewer")
    assert memory.events(subject(c)) == []


def test_a_pending_retraction_marks_the_event_and_changes_nothing(build):
    memory, keys, _, _ = build(msg("m", "2024-03-01", "Kate Reed moved to Bristol in 2021.", ev("moved to", "Kate Reed", "2021", o="Bristol")),
                               msg("r", "2024-03-02", "Please disregard what I wrote about Kate."))
    found = paths.retrieve(memory, "Kate Reed Bristol", ["s1"], paths.Budget(k=10))
    item = next(i for i in found.items if i.observation_id == keys["m"])
    assert any(n.startswith("pending retraction") for n in item.notes)
    assert len(memory.events(subject(event(memory)))) == 1


def test_an_allegation_stays_an_allegation(build):
    memory, _, statuses, _ = build(msg("a", "2024-03-01", "Bram Oster allegedly bought Sefton Mill in 2021.",
                                       ev("bought", "Bram Oster", "2021", o="Sefton Mill", ok=O, allegation=True)))
    assert [s for _, s in statuses] == ["review"] and not [c for c in memory.all_claims() if c.type == EVENT_TYPE]


def test_the_migration_only_adds(driver, database):
    from pathlib import Path

    from gupi import migrations
    text = (Path(migrations.BUILTIN) / "core" / "0013_event_statement.schema.tql").read_text()
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    assert "undefine" not in body and "redefine" not in body
