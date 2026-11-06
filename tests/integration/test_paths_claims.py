"""Claim-path retrieval through the protected pipeline on a live TypeDB: temporal regressions and integrity.
Synthetic, developer-authored worlds. Every claim is formed by formation:v1; nothing here approves a review item."""

from datetime import datetime, timezone

import pytest

from gupi import paths
from gupi.benchmarks import phase8_paths as runner
from gupi.formation import store
from gupi.memory import Memory
from gupi.query import Question
from gupi.temporal import Answer

pytestmark = pytest.mark.integration
P, O, U = "person", "organization", "unclassified"


def emp(n, o, *t, **k):
    return dict(rel="employment", p=[["employee", n, P], ["employer", o, O]], t=[list(x) for x in t], **k)


def st(s, pred, o, *t, sk=O, ok=O, **k):
    return dict(rel="statement", p=[["subject", s, sk], ["object", o, ok]], t=[list(x) for x in t], pred=pred, **k)


def msg(key, at, text, *a, ctx="log", author="Ada Finch"):
    return dict(key=key, context=ctx, at=f"{at}T09:00:00Z", author=author, text=text, assertions=list(a))


def world(*messages, never=()):
    return dict(messages=list(messages), identity=dict(never_merge=list(never)))


@pytest.fixture
def build(driver, database):
    def _build(w):
        clock = runner.Clock()
        memory = Memory.open(database, packs=("core", "people"), driver=driver, clock=clock)
        keys, _ = runner.build(memory, clock, w)
        return memory, keys, sorted({m["context"] for m in w["messages"]})
    return _build


def utc(y, m=6):
    return datetime(y, m, 1, tzinfo=timezone.utc)


def employment(memory):
    return next(c for c in memory.all_claims() if c.type == "employment")


def ask(memory, claim, at):
    return memory.query(Question(claim.type, {k: v[0] for k, v in claim.roles.items()}, at, semantics="v2")).answer


def two_hop(found, *labels):
    return [p for p in found.paths if len(p.hops) == 2 and p.labels[0] == labels[0] and p.labels[-1] == labels[-1]]


JOIN_LEAVE = (msg("j", "2020-02-01", "Mina Roth joined Arbor Mills in 2020.", emp("Mina Roth", "Arbor Mills", ("2020", "start"))),
              msg("l", "2023-02-01", "Mina Roth left Arbor Mills in 2022.", emp("Mina Roth", "Arbor Mills", ("2022", "end"))))


# --- the seven temporal regressions ----------------------------------------------------------------------

def test_employment_before_departure_is_presumed_not_confirmed(build):
    memory, _, ctx = build(world(*JOIN_LEAVE, msg("e", "2021-07-01", "Arbor Mills bought Sefton Mill in 2021.",
                                                  st("Arbor Mills", "bought", "Sefton Mill", ("2021", "start")))))
    assert ask(memory, employment(memory), utc(2021)) is Answer.PRESUMED
    (p, *_) = two_hop(memory.retrieve("Was Mina Roth at Arbor Mills when it bought Sefton Mill?", ctx), "Mina Roth", "Sefton Mill")
    assert p.overlap == "presumed"


def test_employment_after_departure_does_not_overlap(build):
    memory, _, ctx = build(world(*JOIN_LEAVE, msg("e", "2024-07-01", "Arbor Mills bought Sefton Mill in 2024.",
                                                  st("Arbor Mills", "bought", "Sefton Mill", ("2024", "start")))))
    assert ask(memory, employment(memory), utc(2024)) is Answer.FALSE
    (p, *_) = two_hop(memory.retrieve("Was Mina Roth at Arbor Mills when it bought Sefton Mill?", ctx), "Mina Roth", "Sefton Mill")
    assert p.overlap == "none"


def test_an_undated_relationship_is_unknown_never_assumed(build):
    memory, _, ctx = build(world(msg("a", "2021-02-01", "Mina Roth works at Arbor Mills.", emp("Mina Roth", "Arbor Mills")),
                                 msg("b", "2021-03-01", "Arbor Mills owns Sefton Mill.", st("Arbor Mills", "owns", "Sefton Mill"))))
    (p, *_) = two_hop(memory.retrieve("What does Mina Roth's employer own?", ctx), "Mina Roth", "Sefton Mill")
    assert p.overlap == "unknown"


def test_a_gap_between_employment_periods_is_not_continuity(build):
    memory, _, ctx = build(world(*JOIN_LEAVE, msg("r", "2024-02-01", "Mina Roth joined Arbor Mills in 2024.", emp("Mina Roth", "Arbor Mills", ("2024", "start"))),
                                 msg("e", "2023-07-01", "Arbor Mills bought Sefton Mill in 2023.", st("Arbor Mills", "bought", "Sefton Mill", ("2023", "start")))))
    assert ask(memory, employment(memory), utc(2023)) not in (Answer.TRUE, Answer.PRESUMED)
    (p, *_) = two_hop(memory.retrieve("Was Mina Roth at Arbor Mills when it bought Sefton Mill?", ctx), "Mina Roth", "Sefton Mill")
    assert p.overlap in ("none", "unknown")


def test_conflicting_dates_stay_visible_and_are_not_resolved(build):
    memory, keys, ctx = build(world(*JOIN_LEAVE,
                                    msg("x", "2021-07-01", "Arbor Mills bought Sefton Mill in 2021.", st("Arbor Mills", "bought", "Sefton Mill", ("2021", "start"))),
                                    msg("y", "2022-07-01", "Arbor Mills bought Sefton Mill in 2022, not 2021.", st("Arbor Mills", "bought", "Sefton Mill", ("2022", "start"), ev="Arbor Mills bought Sefton Mill in 2022"), author="Joel Hart")))
    found = memory.retrieve("Was Mina Roth at Arbor Mills when it bought Sefton Mill?", ctx)
    hops = [h for p in two_hop(found, "Mina Roth", "Sefton Mill") for h in p.hops if h.relation == "bought"]
    assert hops and all(h.tier == "qualified" and "sources disagree on the date" in h.notes for h in hops)
    assert all(p.overlap != "confirmed" for p in two_hop(found, "Mina Roth", "Sefton Mill"))
    assert {keys["x"], keys["y"]} <= set(found.ids)


def test_explicit_and_inferred_dates_are_preserved(build):
    memory, keys, ctx = build(world(msg("a", "2021-05-03", "Mina Roth joined Arbor Mills in March.", emp("Mina Roth", "Arbor Mills", ("March", "start"))),
                                    msg("b", "2021-05-04", "Sefton Mill opened in March 2021.", st("Sefton Mill", "opened", "Arbor Mills", ("March 2021", "start"), ev="Sefton Mill opened"))))
    stored = [store.get(memory, c.candidate_id) for c in memory.all_claims() if c.candidate_id]
    flags = {s.candidate.times[0].phrase: s.candidate.times[0].explicit for s in stored if s.candidate.times}
    assert flags["March"] is False                       # the year was inferred: retrieval leaves that on record
    assert memory.retrieve("Mina Roth", ctx).ids


def test_connected_relationships_that_never_held_together(build):
    memory, _, ctx = build(world(
        msg("a", "2018-02-01", "Mina Roth joined Arbor Mills in 2018.", emp("Mina Roth", "Arbor Mills", ("2018", "start"))),
        msg("b", "2020-02-01", "Mina Roth left Arbor Mills in 2019.", emp("Mina Roth", "Arbor Mills", ("2019", "end"))),
        msg("c", "2022-07-01", "Arbor Mills partnered with Sefton Mill in 2022.", st("Arbor Mills", "partnered with", "Sefton Mill", ("2022", "start")))))
    found = memory.retrieve("Is Mina Roth connected to Sefton Mill?", ctx)
    (p, *_) = two_hop(found, "Mina Roth", "Sefton Mill")
    assert p.overlap == "none"
    assert any("at the same time: none" in line for line in paths.render(found))
    reverse = two_hop(found, "Sefton Mill", "Mina Roth")
    assert reverse and all(x.overlap == "none" for x in reverse)    # the same whichever end the path starts from


# --- paths and evidence -----------------------------------------------------------------------------------

CHAIN = (msg("a", "2021-02-01", "Mina Roth works at Arbor Mills.", emp("Mina Roth", "Arbor Mills")),
         msg("b", "2021-03-01", "Arbor Mills acquired Sefton Mill.", st("Arbor Mills", "acquired", "Sefton Mill"), ctx="deals"),
         msg("c", "2021-04-01", "Sefton Mill developed Project Birch.", st("Sefton Mill", "developed", "Project Birch", ok=U), ctx="projects"))


def test_a_path_crosses_conversations_only_through_accepted_identity(build):
    memory, keys, ctx = build(world(*CHAIN))
    found = memory.retrieve("What is Mina Roth's employer connected to?", ctx)
    (p, *_) = [x for x in found.paths if x.labels == ("Mina Roth", "Arbor Mills", "Sefton Mill")]
    assert [h.relation for h in p.hops] == ["employment", "acquired"]
    assert [h.observations for h in p.hops] == [(keys["a"],), (keys["b"],)]


def test_without_accepted_identity_threads_do_not_connect(driver, database):
    clock = runner.Clock()
    memory = Memory.open(database, packs=("core", "people"), driver=driver, clock=clock)
    runner.build(memory, clock, world(*CHAIN, never=["Arbor Mills", "Sefton Mill"]))
    found = memory.retrieve("What is Mina Roth's employer connected to?", ["log", "deals", "projects"])
    assert not [p for p in found.paths if len(p.hops) == 2]


def test_every_hop_has_evidence_and_two_hops_is_the_limit(build):
    memory, _, ctx = build(world(*CHAIN))
    found = memory.retrieve("Mina Roth Arbor Mills", ctx)
    assert found.paths and all(h.observations for p in found.paths for h in p.hops)
    assert max(len(p.hops) for p in found.paths) <= 2


def test_max_paths_truncates_and_says_so(build):
    people = [msg(f"p{i}", "2021-02-01", f"Worker{chr(97 + i)} Roth works at Arbor Mills.", emp(f"Worker{chr(97 + i)} Roth", "Arbor Mills")) for i in range(8)]
    memory, _, ctx = build(world(*people))
    found = memory.retrieve("Who works at Arbor Mills?", ctx, paths.Budget(max_paths=3))
    assert len(found.paths) == 3 and "max_paths" in found.truncated


def test_the_hub_rule_stops_crossing_an_unnamed_hub(build):
    people = [msg(f"p{i}", "2021-02-01", f"Worker{chr(97 + i)} Roth works at Arbor Mills.", emp(f"Worker{chr(97 + i)} Roth", "Arbor Mills")) for i in range(6)]
    memory, _, ctx = build(world(*people))
    found = memory.retrieve("Workera Roth colleague", ctx, paths.Budget(hub=3))
    assert "hub" in found.truncated and not [p for p in found.paths if len(p.hops) == 2]


def test_retrieval_is_deterministic_and_writes_nothing(build):
    memory, _, ctx = build(world(*CHAIN))
    before = len(memory.all_claims()), len(store.pending(memory))
    runs = [memory.retrieve("Mina Roth employer", ctx) for _ in range(3)]
    assert runs[0].items == runs[1].items == runs[2].items and runs[0].paths == runs[2].paths
    assert (len(memory.all_claims()), len(store.pending(memory))) == before


def test_without_claims_retrieval_equals_conversational(build):
    memory, _, ctx = build(world(msg("a", "2021-02-01", "The pottery class moved to Tuesday."),
                                 msg("b", "2021-02-02", "Good to know, thanks.")))
    assert memory.retrieve("pottery class", ctx).ids == paths.conversational(memory, "pottery class", ctx).ids


# --- integrity ----------------------------------------------------------------------------------------

def test_a_plain_fact_across_threads_stays_accepted_and_appears_once(build):
    # review defects: an identity claim's evidence is not this fact's evidence, and an item is never returned twice
    memory, keys, ctx = build(world(*CHAIN))
    found = memory.retrieve("Mina Roth employer Arbor Mills", ctx, paths.Budget(k=10))
    item = next(i for i in found.items if i.observation_id == keys["a"])
    assert item.tier == "accepted" and item.notes == ()
    assert len(found.ids) == len(set(found.ids))


def test_an_allegation_is_never_a_hop_and_stays_attributed(build):
    text = "The report alleges that Arbor Mills' treasurer, Mina Roth, hid losses."
    memory, keys, ctx = build(world(msg("a", "2022-02-01", text,
                                        dict(rel="employment", p=[["employee", "Mina Roth", P], ["employer", "Arbor Mills", O]], t=[], ev="Arbor Mills' treasurer, Mina Roth", title="treasurer"),
                                        dict(rel="statement", p=[["subject", "Mina Roth", P]], t=[], pred="hid", obj_text="losses", attr=["reported", "The report", "unknown"], allegation=True, ev=text.rstrip("."))),
                                    msg("b", "2022-03-01", "Arbor Mills owns Sefton Mill.", st("Arbor Mills", "owns", "Sefton Mill"))))
    found = memory.retrieve("Is Mina Roth the treasurer of Arbor Mills?", ctx)
    item = next(i for i in found.items if i.observation_id == keys["a"])
    assert item.tier == "unresolved"
    assert not [p for p in found.paths if "Mina Roth" in p.labels]    # review items are not claims


def test_a_reported_claim_keeps_its_source_on_the_path_and_in_the_text(build):
    memory, keys, ctx = build(world(msg("a", "2022-02-01", "According to Arbor Mills, Mina Roth advises Sefton Mill.",
                                        st("Mina Roth", "advises", "Sefton Mill", sk=P, ev="Mina Roth advises Sefton Mill", attr=["reported", "Arbor Mills", "organisation"]))))
    found = memory.retrieve("Who says Mina Roth advises Sefton Mill?", ctx)
    item = next(i for i in found.items if i.observation_id == keys["a"])
    assert item.tier == "qualified" and item.originators == ("Arbor Mills",)
    assert all(h.tier == "qualified" for p in found.paths for h in p.hops)
    assert any("asserted by Arbor Mills" in line for line in paths.render(found))


BRYN = (msg("a", "2024-04-01", "Bryn Castell manages Arbor Mills.", st("Bryn Castell", "manages", "Arbor Mills", sk=P)),
        msg("o", "2024-04-01", "Kit Sorel manages Sefton Mill.", st("Kit Sorel", "manages", "Sefton Mill", sk=P)),
        msg("r", "2024-04-02", "Apologies, please disregard what I wrote about Bryn, wrong person."))


def test_a_pending_retraction_qualifies_the_claim_and_the_hop_but_changes_nothing(build):
    memory, keys, ctx = build(world(*BRYN))
    found = memory.retrieve("Who manages Arbor Mills?", ctx)
    item = next(i for i in found.items if i.observation_id == keys["a"])
    assert item.tier == "qualified" and any(keys["r"] in n for n in item.notes)
    hops = [h for p in found.paths for h in p.hops if keys["a"] in h.observations]
    assert hops and all(h.tier == "qualified" for h in hops)
    assert keys["r"] in found.ids                                    # the retraction itself stays in view
    claim = next(c for c in memory.all_claims() if keys["a"] in {e.observation_id for e in c.evidence} and c.type == "statement")
    assert claim.id in memory.believed_ids(memory.clock())           # it is a note, not a verdict


def test_a_retraction_about_someone_else_does_not_touch_this_claim(build):
    memory, keys, ctx = build(world(*BRYN))
    item = next(i for i in memory.retrieve("Who manages Sefton Mill?", ctx).items if i.observation_id == keys["o"])
    assert not any("pending" in n for n in item.notes)


def test_a_decided_retraction_is_no_longer_pending(build):
    memory, keys, ctx = build(world(*BRYN))
    (pending, ) = store.pending(memory)
    memory.clock.now = memory.clock.now.replace(year=memory.clock.now.year + 1)
    store.review(memory, pending.candidate.id, "reject", "reviewer-a", "the author confirmed the claim")
    item = next(i for i in memory.retrieve("Who manages Arbor Mills?", ctx).items if i.observation_id == keys["a"])
    assert not any("pending" in n for n in item.notes)


def test_a_same_named_person_is_reported_and_not_merged(build):
    memory, keys, ctx = build(world(msg("a", "2022-02-01", "Sam Whitlock works at Arbor Mills.", emp("Sam Whitlock", "Arbor Mills"), ctx="chat-a"),
                                    msg("b", "2022-02-02", "Sam Whitlock works at Sefton Mill.", emp("Sam Whitlock", "Sefton Mill"), ctx="chat-b"),
                                    never=["Sam Whitlock"]))
    found = memory.retrieve("Where does Sam Whitlock work?", ctx)
    assert found.ambiguous == ["Sam Whitlock"] and {keys["a"], keys["b"]} <= set(found.ids)
    assert not any({"Arbor Mills", "Sefton Mill"} <= set(p.labels) for p in found.paths)
    assert any("several people" in line for line in paths.render(found))


def test_a_withheld_event_is_shown_as_unresolved_and_is_not_traversed(build):
    memory, keys, ctx = build(world(msg("a", "2023-02-01", "Arbor Mills fined Sefton Mill in 2023.", st("Arbor Mills", "fined", "Sefton Mill", ("2023", "holds-at")))))
    found = memory.retrieve("Did Arbor Mills fine Sefton Mill?", ctx)
    assert next(i for i in found.items if i.observation_id == keys["a"]).tier == "unresolved"
    assert not found.paths


def test_belief_time_applies_to_paths(build):
    memory, keys, ctx = build(world(*CHAIN))
    assert not memory.retrieve("Mina Roth employer", ctx, believed_at=datetime(2021, 2, 1, 9, tzinfo=timezone.utc)).paths
