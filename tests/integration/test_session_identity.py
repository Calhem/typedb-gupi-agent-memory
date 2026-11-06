"""Identity across one user's sessions. Same names, aliases, changing roles and references across sessions, through
the protected pipeline. Scripted worlds. Nothing here is accepted except where a test acts as the human reviewer."""

from datetime import datetime, timezone

import pytest

from gupi import identity, paths
from gupi.benchmarks import phase8_paths as runner
from gupi.identity import SESSION_METHOD, Suggestion, link_sessions, participant_id
from gupi.memory import Memory
from gupi.query import Question
from gupi.records import Evidence
from gupi.status import Status
from gupi.temporal import Answer

pytestmark = pytest.mark.integration
P, O = "person", "organization"


def emp(n, o, *t, **k):
    return dict(rel="employment", p=[["employee", n, P], ["employer", o, O]], t=[list(x) for x in t], **k)


def st(s, pred, o, sk=P, ok=O):
    return dict(rel="statement", p=[["subject", s, sk], ["object", o, ok]], t=[], pred=pred)


def msg(key, session, day, text, *a, author="Juno"):
    return dict(key=key, context=session, at=f"{day}T09:00:00Z", author=author, text=text, assertions=list(a))


@pytest.fixture
def build(driver, database):
    def _build(*messages):
        clock = runner.Clock()
        memory = Memory.open(database, packs=("core", "people"), driver=driver, clock=clock)
        keys, _ = runner.build(memory, clock, dict(messages=list(messages), identity=dict(never_merge=[])))
        return memory, keys, clock
    return _build


def no_suggestions(monkeypatch):
    monkeypatch.setattr(Memory, "suggest_identities", lambda self, record=True: [])


@pytest.fixture(autouse=True)
def only_session_links(monkeypatch):
    no_suggestions(monkeypatch)


def links(memory):
    return [c for c in memory.identity_claims() if c.method == SESSION_METHOD]


def referents(memory, label):
    return sorted({r for c in memory.all_claims() if c.type != "identity" for rs in c.roles.values()
                   for r in ((rs,) if isinstance(rs, str) else rs)
                   if memory.claims_about(r) and _label(memory, r) == label})


def _label(memory, rid):
    from gupi import typeql
    from gupi.typedb.connection import transaction
    from typedb.driver import TransactionType
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        return typeql.documents(tx, 'match $x isa referent, has gupi-id == $id; fetch { "l": $x.label };', {"id": rid})[0]["l"]


# --- speakers ------------------------------------------------------------------------------------------------

def test_a_platform_speaker_key_is_one_referent_and_needs_no_link():
    assert participant_id("u1", "user") == participant_id("u1", "user")
    assert participant_id("u1", "user") != participant_id("u2", "user")
    assert participant_id("u1", "user") != participant_id("u1", "assistant")


# --- same names ----------------------------------------------------------------------------------------------

def test_two_people_with_one_name_in_different_users_are_never_compared(build):
    memory, _, _ = build(
        msg("a", "u1:s1", "2024-01-02", "Alex Reed joined Fenwick Labs in 2020.", emp("Alex Reed", "Fenwick Labs", ("2020", "start"))),
        msg("b", "u2:s1", "2024-01-03", "Alex Reed joined Fenwick Labs in 2020.", emp("Alex Reed", "Fenwick Labs", ("2020", "start"))))
    found = link_sessions(memory, ["u1:s1"]), link_sessions(memory, ["u2:s1"])
    assert not any(f.linked or f.name_only for f in found) and not links(memory)


def test_a_shared_name_alone_links_nothing(build):
    memory, _, _ = build(
        msg("a", "s1", "2024-01-02", "Alex Reed joined Fenwick Labs in 2020.", emp("Alex Reed", "Fenwick Labs", ("2020", "start"))),
        msg("b", "s2", "2024-02-02", "Alex Reed joined Arbor Mills in 2021.", emp("Alex Reed", "Arbor Mills", ("2021", "start"))))
    found = link_sessions(memory, ["s1", "s2"])
    assert not found.linked and [n[2] for n in found.name_only] == ["Alex Reed"]
    assert not links(memory)


def test_a_second_signal_gives_a_labelled_hypothesis_never_a_merge(build):
    memory, _, _ = build(
        msg("a", "s1", "2024-01-02", "Alex Reed joined Fenwick Labs in 2020.", emp("Alex Reed", "Fenwick Labs", ("2020", "start"))),
        msg("b", "s2", "2024-02-02", "Alex Reed left Fenwick Labs in 2023.", emp("Alex Reed", "Fenwick Labs", ("2023", "end"))))
    found = link_sessions(memory, ["s1", "s2"])
    (s,) = [x for x in found.linked if "Alex" in x.reason]
    assert "connected by claims to 'fenwick labs'" in s.reason and s.score < 0.7
    (claim,) = [c for c in links(memory) if "Alex" in c.values["reason"]]
    assert claim.status_at(memory.clock()) is Status.HYPOTHESIS and claim.basis == "inferred"
    assert not memory.identity_groups(memory.clock())


def test_uncertain_links_never_change_an_answer(build):
    memory, _, clock = build(
        msg("a", "s1", "2024-01-02", "Alex Reed joined Fenwick Labs in 2020.", emp("Alex Reed", "Fenwick Labs", ("2020", "start"))),
        msg("b", "s2", "2024-02-02", "Alex Reed left Fenwick Labs in 2023.", emp("Alex Reed", "Fenwick Labs", ("2023", "end"))))
    joined = next(c for c in memory.all_claims() if c.valid.from_earliest is not None)
    roles = {k: v[0] for k, v in joined.roles.items()}
    at = datetime(2024, 6, 1, tzinfo=timezone.utc)

    def answer():
        return memory.query(Question("employment", roles, at, semantics="v2")).answer
    before = answer()
    link_sessions(memory, ["s1", "s2"])
    assert before is not Answer.FALSE and answer() is before         # the departure belongs to an unconfirmed person
    clock.now = clock.now.replace(year=clock.now.year + 1)
    for c in links(memory):
        memory.review(c.id, "accepted", "human-reviewer")
    assert answer() is Answer.FALSE                                  # one reviewer decision, and only then


def test_a_speaker_of_that_name_is_a_signal_but_not_proof(build):
    memory, _, _ = build(
        msg("a", "s1", "2024-01-02", "Bram Oster joined Fenwick Labs in 2020.", emp("Bram Oster", "Fenwick Labs", ("2020", "start")), author="Bram Oster"),
        msg("b", "s1", "2024-01-03", "Bram Oster joined Arbor Mills in 2021.", emp("Bram Oster", "Arbor Mills", ("2021", "start"))))
    found = link_sessions(memory, ["s1"])
    (s,) = found.linked
    assert "is a speaker in a session" in s.reason
    assert links(memory)[0].status_at(memory.clock()) is Status.HYPOTHESIS


def test_links_are_not_proposed_twice_and_a_rejection_stands(build):
    memory, _, clock = build(
        msg("a", "s1", "2024-01-02", "Alex Reed joined Fenwick Labs in 2020.", emp("Alex Reed", "Fenwick Labs", ("2020", "start"))),
        msg("b", "s2", "2024-02-02", "Alex Reed left Fenwick Labs in 2023.", emp("Alex Reed", "Fenwick Labs", ("2023", "end"))))
    link_sessions(memory, ["s1", "s2"])
    count = len(links(memory))
    assert not link_sessions(memory, ["s1", "s2"]).linked
    clock.now = clock.now.replace(year=clock.now.year + 1)
    for c in links(memory):
        memory.review(c.id, "rejected", "human-reviewer")
    assert not link_sessions(memory, ["s1", "s2"]).linked and len(links(memory)) == count
    assert not memory.identity_groups(clock.now)


# --- aliases -----------------------------------------------------------------------------------------------------

def test_a_first_name_links_to_a_full_name_only_with_a_second_signal(build):
    memory, _, _ = build(
        msg("a", "s1", "2024-01-02", "Priya Shah joined Northwind in 2020.", emp("Priya Shah", "Northwind", ("2020", "start"))),
        msg("b", "s2", "2024-02-02", "Priya joined Northwind in 2020.", emp("Priya", "Northwind", ("2020", "start"))),
        msg("c", "s3", "2024-03-02", "Priya joined Arbor Mills in 2021.", emp("Priya", "Arbor Mills", ("2021", "start"))))
    found = link_sessions(memory, ["s1", "s2", "s3"])
    assert any("alias name" in s.reason for s in found.linked)
    assert any(n[2] in ("Priya", "Priya Shah") for n in found.name_only)      # s3 shares only the first name


def test_a_nickname_is_left_to_a_reviewer(build):
    memory, keys, clock = build(
        msg("a", "s1", "2024-01-02", "Josephine Hale joined Northwind in 2020.", emp("Josephine Hale", "Northwind", ("2020", "start"))),
        msg("b", "s2", "2024-02-02", "Jo joined Northwind in 2020.", emp("Jo", "Northwind", ("2020", "start"))))
    assert not [s for s in link_sessions(memory, ["s1", "s2"]).linked if "Jo" in s.reason]
    a, b = referents(memory, "Josephine Hale")[0], referents(memory, "Jo")[0]
    (claim_id,) = identity.record(memory, [Suggestion(a, b, P, 1.0, "the owner says Jo is Josephine Hale",
                                                      (Evidence(keys["a"]), Evidence(keys["b"])))])
    clock.now = clock.now.replace(year=clock.now.year + 1)
    memory.review(claim_id, "accepted", "human-reviewer")
    assert memory.identity_groups(clock.now)[a] == {a, b}


# --- changing roles ----------------------------------------------------------------------------------------------

def test_a_changing_role_keeps_its_periods_after_a_reviewer_accepts_the_link(build):
    memory, _, clock = build(
        msg("a", "s1", "2024-01-02", "Mina Roth joined Arbor Mills as engineer in 2019.", emp("Mina Roth", "Arbor Mills", ("2019", "start"), title="engineer")),
        msg("b", "s2", "2024-02-02", "Mina Roth left Arbor Mills in 2021.", emp("Mina Roth", "Arbor Mills", ("2021", "end"))),
        msg("c", "s3", "2024-03-02", "Mina Roth joined Arbor Mills as director in 2023.", emp("Mina Roth", "Arbor Mills", ("2023", "start"), title="director")))
    link_sessions(memory, ["s1", "s2", "s3"])
    clock.now = clock.now.replace(year=clock.now.year + 1)
    for c in links(memory):
        memory.review(c.id, "accepted", "human-reviewer")
    first = next(c for c in memory.all_claims() if c.values.get("job-title") == "engineer")
    roles = {k: v[0] for k, v in first.roles.items()}
    ask = lambda y: memory.query(Question("employment", roles, datetime(y, 6, 1, tzinfo=timezone.utc), semantics="v2")).answer
    assert ask(2022) is Answer.FALSE             # the gap stays a gap: two roles are not one continuous spell
    assert ask(2024) is not Answer.FALSE         # and the later period is found through the accepted link


# --- references across sessions ------------------------------------------------------------------------------------

WORLD = (msg("a", "s1", "2024-01-02", "Alex Reed runs the Harbour project.", st("Alex Reed", "runs", "Harbour project", ok="unclassified")),
         msg("b", "s2", "2024-02-02", "Alex Reed runs the Harbour project.", st("Alex Reed", "runs", "Harbour project", ok="unclassified")),
         msg("c", "s2", "2024-02-03", "Alex Reed mentors Dana Voss.", st("Alex Reed", "mentors", "Dana Voss", ok=P)))


def walk(memory, *flags, q="Who is on the Harbour project?"):
    return paths.retrieve(memory, q, ["s1", "s2"], paths.Budget(k=10, unresolved_links=bool(flags)))


def test_retrieval_ignores_unreviewed_links_unless_asked(build):
    memory, keys, _ = build(*WORLD)
    link_sessions(memory, ["s1", "s2"])
    assert not [p for p in walk(memory).paths if any(h.tier == "unresolved" for h in p.hops)]


CROSSING = (msg("a", "s1", "2024-01-02", "Alex Reed runs the Harbour project.", st("Alex Reed", "runs", "Harbour project", ok="unclassified")),
            msg("b", "s1", "2024-01-03", "Alex Reed joined Fenwick Labs in 2020.", emp("Alex Reed", "Fenwick Labs", ("2020", "start"))),
            msg("c", "s2", "2024-02-02", "Alex Reed joined Fenwick Labs in 2020.", emp("Alex Reed", "Fenwick Labs", ("2020", "start"))),
            msg("d", "s2", "2024-02-03", "Alex Reed mentors Dana Voss.", st("Alex Reed", "mentors", "Dana Voss", ok=P)))


def test_a_reference_across_sessions_comes_back_labelled_unresolved(build):
    memory, keys, _ = build(*CROSSING)
    link_sessions(memory, ["s1", "s2"])
    found = walk(memory, True, q="What is the Harbour project?")
    crossing = [p for p in found.paths if p.labels[-1] == "Dana Voss" and any(h.tier == "unresolved" for h in p.hops)]
    assert crossing and "identity not confirmed" in " ".join(crossing[0].hops[1].notes)
    item = next(i for i in found.items if i.observation_id == keys["d"])
    assert item.tier == "unresolved" and any(n.startswith("identity not confirmed") for n in item.notes)
    assert any("unresolved: identity not confirmed" in line for line in paths.render(found))


def test_an_accepted_identity_never_returns_another_users_text(build):
    memory, keys, clock = build(*CROSSING)
    a, b = sorted(r for r in referents(memory, "Alex Reed"))
    (claim,) = identity.record(memory, [Suggestion(a, b, P, 1.0, "accepted across users",
                                                   (Evidence(keys["b"]), Evidence(keys["c"])))])
    clock.now = clock.now.replace(year=clock.now.year + 1)
    memory.review(claim, "accepted", "human-reviewer")
    found = paths.retrieve(memory, "What is the Harbour project?", ["s1"], paths.Budget(k=10))
    assert set(found.ids) <= {keys["a"], keys["b"]}
    assert all(o in {keys["a"], keys["b"]} for p in found.paths for h in p.hops for o in h.observations) or not found.paths
    assert not [p for p in found.paths for h in p.hops if not set(h.observations) & {keys["a"], keys["b"]}]


def test_an_accepted_link_is_walked_as_accepted(build):
    memory, _, clock = build(*WORLD)
    link_sessions(memory, ["s1", "s2"])
    clock.now = clock.now.replace(year=clock.now.year + 1)
    for c in links(memory):
        memory.review(c.id, "accepted", "human-reviewer")
    found = walk(memory, True, q="What is the Harbour project?")
    assert not [h for p in found.paths for h in p.hops if h.tier == "unresolved"]


def test_a_rejected_link_is_not_walked(build):
    memory, _, clock = build(*WORLD)
    link_sessions(memory, ["s1", "s2"])
    clock.now = clock.now.replace(year=clock.now.year + 1)
    for c in links(memory):
        memory.review(c.id, "rejected", "human-reviewer")
    assert not [h for p in walk(memory, True, q="What is the Harbour project?").paths for h in p.hops if h.tier == "unresolved"]


def test_a_link_half_outside_the_scope_is_not_walked(build):
    memory, _, _ = build(*CROSSING)
    link_sessions(memory, ["s1", "s2"])
    found = paths.retrieve(memory, "What is the Harbour project?", ["s1"], paths.Budget(k=10, unresolved_links=True))
    assert not [h for p in found.paths for h in p.hops if h.tier == "unresolved"]
