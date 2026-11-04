"""rules:v2.1 through the candidate store: a pronoun never becomes a believed person (D1), and reporting
unsupported expressions (D2) changes no formation decision."""

from datetime import datetime, timedelta, timezone

import pytest

from gupi.formation import extractors, store
from gupi.records import Batch, Context, Observation, Referent, Source

pytestmark = pytest.mark.integration
SAID = datetime(2025, 8, 20, 9, tzinfo=timezone.utc)
AUTHOR = "p:ivo-marsh"


def submit_all(memory, clock, version, texts):
    ex, prior = extractors.get(version), []
    src, ctx = Source("src:d1", "chat"), Context("ctx:d1", "conversation")
    memory.ingest(Batch(referents=(Referent(AUTHOR, "person", "Ivo Marsh"),)))
    for n, text in enumerate(texts):
        clock.now = SAID + timedelta(minutes=n)
        obs = Observation(src.id, f"m{n}", text, clock.now, ctx.id, AUTHOR)
        memory.ingest(Batch(sources=(src,), observations=(obs,), contexts=(ctx,)))
        cset, report = ex.extract(obs, prior=tuple(prior))
        prior.append(cset)
        if cset.candidates:
            store.submit(memory, obs, cset)
    clock.now = SAID + timedelta(hours=1)


def employees(memory):
    from gupi.query import _labels
    from gupi.typedb.connection import transaction
    from typedb.driver import TransactionType
    believed = memory.believed_ids(memory.clock())
    views = [v for v in memory.all_claims() if v.id in believed and v.type == "employment"]
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        names = _labels(tx, [r for v in views for r in v.roles["employee"]])
    return sorted(names.get(r, r) for v in views for r in v.roles["employee"])


TEXTS = ["Nora Vance joined Halden in March 2025.", "She left Halden in May 2025.", "I joined Halden in June 2024.",
         "Nora Vance quit her job in May."]


def test_v21_forms_no_claim_about_a_pronoun(memory, clock):
    submit_all(memory, clock, "rules:v2.1", TEXTS)
    assert employees(memory) == ["Ivo Marsh", "Nora Vance"]  # "I" is the author; "She" is nobody
    assert not store.pending(memory)


def test_v2_still_forms_it_for_reproducibility(memory, clock):
    submit_all(memory, clock, "rules:v2", TEXTS)
    assert employees(memory) == ["Ivo Marsh", "Nora Vance", "She"]
