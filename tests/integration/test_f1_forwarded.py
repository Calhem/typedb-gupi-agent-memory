"""F1 (docs/evaluation/phase-7b/stage-2b/forwarded-attestations.md): copies never become extra original
attestations; independent assertions stay distinct; evidence counts follow originators, not copies."""

from datetime import datetime, timedelta, timezone

import pytest

from gupi.extraction.contract import referent_id
from gupi.formation import extractors, store
from gupi.records import Batch, Context, Observation, Referent, Source

pytestmark = pytest.mark.integration
START = datetime(2025, 8, 20, 9, tzinfo=timezone.utc)
CTX = "ctx:f1"
LEFT = "Omar Siddiq left Arnholt Systems in June 2025."


def fwd(sender, body=LEFT, note="FYI."):
    head = f"From: {sender}\n" if sender else ""
    return f"{note}\n---- Forwarded message ----\n{head}{body}"


class Mail:
    def __init__(self, memory, clock):
        self.memory, self.clock, self.n, self.prior = memory, clock, 0, []

    def send(self, author, text, key=None, context=CTX):
        self.n += 1
        self.clock.now = START + timedelta(hours=self.n)
        aid = "p:" + author.lower().replace(" ", "-")
        obs = Observation("src:f1", key or f"m{self.n}", text, self.clock.now, context, aid)
        self.memory.ingest(Batch((Source("src:f1", "mail"),), (obs,), (Referent(aid, "person", author),),
                                 contexts=(Context(context, "conversation"),)))
        cset, _ = extractors.get("rules:v2.1").extract(obs, prior=tuple(self.prior))
        self.prior.append(cset)
        self.clock.now += timedelta(minutes=1)
        store.submit(self.memory, obs, cset)
        return [store.get(self.memory, c.id) for c in cset.candidates]


def statuses(stored):
    return [s.status for s in stored]


def employment_claims(memory):
    return [c for c in memory.all_claims() if c.type == "employment"]


def independent(memory, clock, context=CTX):
    roles = {"employee": referent_id(context, "person", "Omar Siddiq"),
             "employer": referent_id(context, "organization", "Arnholt Systems")}
    r = memory.ask("employment", roles, datetime(2025, 8, 1, tzinfo=timezone.utc), clock.now, semantics="v2")
    return r.qualification.independent


def test_one_original_assertion(memory, clock):
    m = Mail(memory, clock)
    assert statuses(m.send("Ivo Marsh", LEFT)) == ["formed"] and independent(memory, clock) == 1


def test_the_same_assertion_forwarded_once(memory, clock):
    m = Mail(memory, clock)
    m.send("Ivo Marsh", LEFT)
    assert statuses(m.send("Wen Abara", fwd("Ivo Marsh"))) == ["withheld"]
    assert len(employment_claims(memory)) == 1 and independent(memory, clock) == 1


def test_a_forwarded_copy_forwarded_again(memory, clock):
    m = Mail(memory, clock)
    assert statuses(m.send("Wen Abara", fwd("Dana Okoro"))) == ["formed"]      # the only attestation we have
    again = m.send("Xu Lin", fwd("Dana Okoro", note="Passing this on."))
    assert statuses(again) == ["withheld"] and "repeats existing claim" in again[0].decisions[0].reason
    assert len(employment_claims(memory)) == 1 and independent(memory, clock) == 1


def test_one_original_in_several_documents(memory, clock):
    m = Mail(memory, clock)
    m.send("Wen Abara", fwd("Dana Okoro"))
    for author, note in (("Xu Lin", "See below."), ("Ivo Marsh", "Heads up."), ("Bo Kim", "For the record.")):
        assert statuses(m.send(author, fwd("Dana Okoro", note=note))) == ["withheld"]
    assert len(employment_claims(memory)) == 1 and independent(memory, clock) == 1


def test_two_genuinely_independent_assertions_stay_distinct(memory, clock):
    m = Mail(memory, clock)
    assert statuses(m.send("Ivo Marsh", LEFT)) == ["formed"]
    assert statuses(m.send("Wen Abara", LEFT)) == ["formed"]
    assert len(employment_claims(memory)) == 2 and independent(memory, clock) == 2


def test_two_people_quoting_the_same_original_source(memory, clock):
    m = Mail(memory, clock)
    quoted = "Dana Okoro told me that Omar Siddiq left Arnholt Systems in June 2025."
    assert statuses(m.send("Ivo Marsh", quoted)) == ["formed"] and statuses(m.send("Wen Abara", quoted)) == ["formed"]
    assert len(employment_claims(memory)) == 2                                  # two reports, kept
    assert independent(memory, clock) == 1                                      # one originator


def test_repeated_ingestion_of_the_same_forwarded_document(memory, clock):
    m = Mail(memory, clock)
    first = m.send("Wen Abara", fwd("Dana Okoro"), key="same")
    again = m.send("Wen Abara", fwd("Dana Okoro"), key="same")
    assert [s.candidate.id for s in first] == [s.candidate.id for s in again]
    assert len(employment_claims(memory)) == 1 and len(again[0].decisions) == 1


def test_forwarded_copies_with_incomplete_provenance_are_not_corroboration(memory, clock):
    m = Mail(memory, clock)
    assert statuses(m.send("Wen Abara", fwd(None))) == ["formed"]
    assert statuses(m.send("Xu Lin", fwd(None, note="Passing on."))) == ["withheld"]
    assert len(employment_claims(memory)) == 1 and independent(memory, clock) == 1


def test_different_original_claimants_are_not_copies(memory, clock):
    m = Mail(memory, clock)
    m.send("Wen Abara", fwd("Dana Okoro"))
    assert statuses(m.send("Xu Lin", fwd("Ravi Menon"))) == ["formed"]          # a second originator
    assert len(employment_claims(memory)) == 2 and independent(memory, clock) == 2


def test_a_correction_to_a_forwarded_assertion(memory, clock):
    m = Mail(memory, clock)
    (forwarded,) = m.send("Wen Abara", fwd("Dana Okoro"))
    before = memory.believed_ids(clock())
    (fix,) = m.send("Dana Okoro", "Correction: Omar Siddiq left Arnholt Systems in July 2025, not June.")
    assert fix.status == "review" and forwarded.claim_id in fix.suggestions[0].targets
    assert set(before) <= memory.believed_ids(clock()) and not [c for c in memory.all_claims() if c.superseded_by]
