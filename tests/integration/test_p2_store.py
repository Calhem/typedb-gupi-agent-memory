"""P2 through the store on a live TypeDB: the relation links author and person, and nothing is merged by name."""

import pytest

from gupi import paths
from gupi.benchmarks import phase8_paths as runner
from gupi.formation import store
from gupi.identity import SESSION_METHOD, link_sessions
from gupi.memory import Memory

pytestmark = pytest.mark.integration
P, O, U = "person", "organization", "unclassified"


def kin(ev, name, noun, **k):
    return dict(ev=ev, rel="statement", p=[["subject", ev.split()[0], P], ["object", name, P]], t=[], pred=noun, **k)


def boss(ev, name):
    return dict(ev=ev, rel="reporting", p=[["report", "My", P], ["manager", name, P]], t=[])


def st(ev, s, pred, o, ok=U):
    return dict(ev=ev, rel="statement", p=[["subject", s, P], ["object", o, ok]], t=[], pred=pred)


def emp(ev, n, o):
    return dict(ev=ev, rel="employment", p=[["employee", n, P], ["employer", o, O]], t=[])


def msg(key, ctx, day, text, *a, author="Juno"):
    return dict(key=key, context=ctx, at=f"{day}T09:00:00Z", author=author, text=text, assertions=list(a))


@pytest.fixture
def build(driver, database, monkeypatch):
    monkeypatch.setattr(Memory, "suggest_identities", lambda self, record=True: [])

    def _build(*messages):
        clock = runner.Clock()
        memory = Memory.open(database, packs=("core", "people"), driver=driver, clock=clock)
        keys, statuses = runner.build(memory, clock, dict(messages=list(messages), identity=dict(never_merge=[])))
        return memory, keys, statuses, clock
    return _build


KATE = msg("a", "s1", "2024-01-02", "My sister Kate lives in Bristol.", kin("My sister Kate", "Kate", "sister"),
           st("Kate lives in Bristol", "Kate", "lives in", "Bristol"))


def test_the_relation_links_the_author_to_the_named_person(build):
    memory, keys, statuses, _ = build(KATE)
    assert [s for _, s in statuses] == ["formed", "formed"]
    relation = next(c for c in memory.all_claims() if c.values.get("predicate-text") == "sister")
    assert relation.roles["subject"] == ("a:Juno",) or relation.roles["subject"] == "a:Juno"
    assert relation.evidence[0].observation_id == keys["a"] and relation.evidence[0].quote == "My sister Kate"


def test_a_manager_becomes_a_reporting_claim_and_a_path(build):
    memory, keys, _, _ = build(msg("a", "s1", "2024-01-02", "My manager Alice works at Meridian.", boss("My manager Alice", "Alice"),
                                   emp("Alice works at Meridian", "Alice", "Meridian")))
    assert {c.type for c in memory.all_claims()} == {"reporting", "employment"}
    found = paths.retrieve(memory, "Where does Juno's manager work?", ["s1"], paths.Budget(k=10))
    assert any(p.labels == ("Juno", "Alice", "Meridian") for p in found.paths)


def test_the_named_person_is_not_merged_with_a_speaker_of_that_name(build):
    memory, _, _, _ = build(msg("s", "s1", "2024-01-01", "Hello.", author="Kate"), KATE)
    kate_author = "a:Kate"
    relation = next(c for c in memory.all_claims() if c.values.get("predicate-text") == "sister")
    assert relation.roles["object"] not in (kate_author, (kate_author,))
    assert not memory.identity_groups(memory.clock())


def test_the_same_name_across_sessions_stays_two_referents_with_at_most_a_hypothesis(build):
    memory, _, _, clock = build(KATE, msg("b", "s2", "2024-02-02", "My sister Kate moved.", kin("My sister Kate", "Kate", "sister")))
    objects = {c.roles["object"] for c in memory.all_claims() if c.values.get("predicate-text") == "sister"}
    assert len(objects) == 2
    linked = link_sessions(memory, ["s1", "s2"]).linked
    assert any("Kate" in s.reason for s in linked)
    assert not memory.identity_groups(clock.now)
    assert all(c.status_at(clock.now).name == "HYPOTHESIS" for c in memory.identity_claims() if c.method == SESSION_METHOD)


def test_two_relations_for_one_name_wait_for_a_reviewer(build):
    memory, _, statuses, _ = build(msg("a", "s1", "2024-01-02", "My sister Kate left.", kin("My sister Kate", "Kate", "sister")),
                                   msg("b", "s1", "2024-01-03", "My colleague Kate left.", kin("My colleague Kate", "Kate", "colleague")))
    assert [s for _, s in statuses] == ["formed", "review"]
    assert [s.status for s in store.pending(memory)] == ["review"]
