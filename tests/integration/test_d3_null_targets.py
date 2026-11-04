"""D3 with format 1.1 (docs/evaluation/phase-7b/stage-2b/correction-targets.md): a correction or retraction
whose target is not established is kept as evidence and reviewed; no target is invented; nothing prior is
changed; a reviewer can assign a target later, auditably."""

from datetime import datetime, timedelta, timezone

import pytest

from gupi import ids
from gupi.formation import extractors, store
from gupi.formation.candidate import (
    IR_VERSION_1_1, Candidate, CandidateSet, Participant, Passage, Relation, TimeEvidence,
)
from gupi.records import Batch, Context, Observation, Source

pytestmark = pytest.mark.integration
START = datetime(2025, 8, 20, 9, tzinfo=timezone.utc)


class Talk:
    def __init__(self, memory, clock, context="ctx:d3n"):
        self.memory, self.clock, self.context, self.n = memory, clock, context, 0

    def observe(self, text):
        self.n += 1
        self.clock.now = START + timedelta(hours=self.n)
        obs = Observation("src:d3n", f"{self.context}-{self.n}", text, self.clock.now, self.context)
        self.memory.ingest(Batch((Source("src:d3n", "chat"),), (obs,), contexts=(Context(self.context, "conversation"),)))
        return obs

    def state(self, text):
        """An ordinary statement, extracted by rules:v2.1 and formed."""
        obs = self.observe(text)
        cset, _ = extractors.get("rules:v2.1").extract(obs)
        self.clock.now += timedelta(minutes=1)
        store.submit(self.memory, obs, cset)
        return store.get(self.memory, cset.candidates[0].id)

    def correct(self, text, kind="corrects", target=None, month="April 2025", polarity="positive"):
        """A 1.1 correction candidate whose relation target is `target` (None: not established)."""
        obs = self.observe(text)
        s, w = text.index("Nora Vance"), text.index("Halden")
        times = ()
        if month in text:
            m = text.index(month)
            times = (TimeEvidence("start", month, m, m + len(month), datetime(2025, 4, 1, tzinfo=timezone.utc),
                                  datetime(2025, 5, 1, tzinfo=timezone.utc), "month"),)
        c = Candidate("employment", Passage(obs.id, 0, len(text), text),
                      (Participant("employee", "Nora Vance", s, s + 10, "person"), Participant("employer", "Halden", w, w + 6, "organization")),
                      times=times, polarity=polarity, relations=(Relation(kind, target, "stated", text.split(",")[0]),))
        cset = CandidateSet(obs.id, ids.content_hash(text), "test:1.1", (c,), IR_VERSION_1_1)
        self.clock.now += timedelta(minutes=1)
        store.submit(self.memory, obs, cset)
        return obs, cset, store.get(self.memory, c.id)


def unchanged(memory, believed_before):
    assert set(believed_before) <= memory.believed_ids(memory.clock())
    assert not [c for c in memory.all_claims() if c.superseded_by]


def test_an_explicit_target_is_resolved_and_reviewed(memory, clock):
    t = Talk(memory, clock)
    first = t.state("Nora Vance joined Halden in March 2025.")
    _, _, fix = t.correct("Correction, Nora Vance joined Halden in April 2025.", target=first.candidate.id)
    assert fix.status == "review" and (fix.suggestions[0].resolution, fix.suggestions[0].targets) == ("resolved", (first.claim_id,))


def test_no_identified_target_is_kept_and_reviewed_without_inventing_one(memory, clock):
    t = Talk(memory, clock)
    _, cset, fix = t.correct("Sorry, Nora Vance joined Halden in April 2025.")
    assert fix.status == "review" and "not established" in fix.decisions[0].reason
    assert fix.candidate.relations[0].target is None                          # stored as the source put it
    assert "Sorry, Nora Vance joined Halden in April 2025." in fix.payload    # the evidence is inspectable
    assert (fix.suggestions[0].resolution, fix.suggestions[0].targets) == ("missing", ())
    unchanged(memory, set())


def test_one_plausible_target_is_listed_but_not_resolved(memory, clock):
    t = Talk(memory, clock)
    first = t.state("Nora Vance joined Halden in March 2025.")
    before = memory.believed_ids(clock())
    _, _, fix = t.correct("Sorry, Nora Vance joined Halden in April 2025.")
    s = fix.suggestions[0]
    assert s.resolution == "ambiguous" and s.targets == (first.claim_id,) and "not established" in s.reason
    unchanged(memory, before)


def test_several_plausible_targets_are_all_listed(memory, clock):
    t = Talk(memory, clock)
    a, b = t.state("Nora Vance joined Halden in February 2025."), t.state("Nora Vance joined Halden in March 2025.")
    _, _, fix = t.correct("Sorry, Nora Vance joined Halden in April 2025.")
    assert fix.suggestions[0].resolution == "ambiguous" and set(fix.suggestions[0].targets) == {a.claim_id, b.claim_id}


def test_a_retraction_without_a_target(memory, clock):
    t = Talk(memory, clock)
    _, _, r = t.correct("Scratch that, Nora Vance did not join Halden.", kind="retracts", month="-", polarity="negative")
    assert r.status == "review" and r.suggestions[0].resolution == "missing"


def test_a_target_in_another_conversation_is_not_matched(memory, clock):
    Talk(memory, clock, "ctx:elsewhere").state("Nora Vance joined Halden in March 2025.")
    _, _, fix = Talk(memory, clock, "ctx:here").correct("Sorry, Nora Vance joined Halden in April 2025.")
    assert fix.suggestions[0].resolution == "missing"


def test_a_superseded_assertion_is_not_offered(memory, clock):
    t = Talk(memory, clock)
    old, new = t.state("Nora Vance joined Halden in March 2025."), t.state("Nora Vance joined Halden in February 2025.")
    clock.now += timedelta(minutes=5)
    memory.supersede(old.claim_id, new.claim_id, reason="test", decided_by="reviewer-a")
    _, _, fix = t.correct("Sorry, Nora Vance joined Halden in April 2025.")
    assert old.claim_id not in fix.suggestions[0].targets


def test_two_corrections_of_the_same_assertion(memory, clock):
    t = Talk(memory, clock)
    first = t.state("Nora Vance joined Halden in March 2025.")
    before = memory.believed_ids(clock())
    _, _, a = t.correct("Sorry, Nora Vance joined Halden in April 2025.")
    _, _, b = t.correct("Correction, Nora Vance joined Halden in April 2025.", target=first.candidate.id)
    assert {a.status, b.status} == {"review"} and first.claim_id in a.suggestions[0].targets + b.suggestions[0].targets
    unchanged(memory, before)


def test_a_reviewer_assigns_the_target_later_and_it_is_audited(memory, clock):
    t = Talk(memory, clock)
    first = t.state("Nora Vance joined Halden in March 2025.")
    t.state("Nora Vance joined Halden in February 2025.")
    _, _, fix = t.correct("Sorry, Nora Vance joined Halden in April 2025.")
    assert fix.suggestions[0].resolution == "ambiguous"
    clock.now += timedelta(minutes=5)
    store.assign_correction_target(memory, fix.candidate.id, first.claim_id, "reviewer-a", "the March statement")
    after = store.get(memory, fix.candidate.id)
    latest = after.suggestions[-1]
    assert (latest.resolution, latest.targets) == ("resolved", (first.claim_id,))
    assert "reviewer-a" in latest.reason and "the March statement" in latest.reason
    assert len(after.suggestions) == 2 and after.suggestions[0].resolution == "ambiguous"  # history kept
    assert not [c for c in memory.all_claims() if c.superseded_by]                         # still nothing applied
    clock.now += timedelta(minutes=1)
    store.assign_correction_target(memory, fix.candidate.id, first.claim_id, "reviewer-a", "the March statement")
    assert len(store.get(memory, fix.candidate.id).suggestions) == 2                          # idempotent


def test_target_assignment_refuses_what_it_cannot_justify(memory, clock):
    t = Talk(memory, clock)
    plain = t.state("Nora Vance joined Halden in March 2025.")
    _, _, fix = t.correct("Sorry, Nora Vance joined Halden in April 2025.")
    clock.now += timedelta(minutes=5)
    with pytest.raises(ValueError, match="not a claim"):
        store.assign_correction_target(memory, fix.candidate.id, "claim:" + "0" * 32, "reviewer-a", "x")
    with pytest.raises(ValueError, match="no stated correction"):
        store.assign_correction_target(memory, plain.candidate.id, plain.claim_id, "reviewer-a", "x")
    with pytest.raises(ValueError, match="reviewer"):
        store.assign_correction_target(memory, fix.candidate.id, plain.claim_id, "", "x")


def test_approving_an_unresolved_correction_changes_no_prior_claim(memory, clock):
    t = Talk(memory, clock)
    first = t.state("Nora Vance joined Halden in March 2025.")
    _, _, fix = t.correct("Sorry, Nora Vance joined Halden in April 2025.")
    clock.now += timedelta(minutes=5)
    store.review(memory, fix.candidate.id, "approve", "reviewer-a")
    assert store.get(memory, fix.candidate.id).status == "formed"
    unchanged(memory, {first.claim_id})


def test_resubmission_is_idempotent(memory, clock):
    t = Talk(memory, clock)
    obs, cset, fix = t.correct("Sorry, Nora Vance joined Halden in April 2025.")
    clock.now += timedelta(minutes=5)
    store.submit(memory, obs, cset)
    again = store.get(memory, fix.candidate.id)
    assert (len(again.decisions), len(again.suggestions)) == (1, 1)


def test_an_inferred_candidate_is_never_formed_automatically(memory, clock):
    """Policy kept (Stage 2B): an inferred statement is representable (basis "inferred"), so it goes to review,
    never into automatic formation."""
    import dataclasses
    t = Talk(memory, clock)
    obs = t.observe("Nora Vance joined Halden in March 2025.")
    cset, _ = extractors.get("rules:v2.1").extract(obs)
    c = dataclasses.replace(cset.candidates[0], basis="inferred")
    inferred = CandidateSet(obs.id, cset.content_hash, cset.extractor, (c,), cset.ir_version)
    clock.now += timedelta(minutes=1)
    store.submit(memory, obs, inferred)
    s = store.get(memory, c.id)
    assert s.status == "review" and "inferred" in s.decisions[0].reason and not memory.all_claims()
