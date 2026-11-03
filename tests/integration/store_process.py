"""A separate process for the candidate-store restart test (test_candidate_store.py). Each run opens its own
TypeDB connection, does one phase, prints JSON and exits, so what survives is what is durable.

    python -I tests/integration/store_process.py DATABASE submit|pending|approve CANDIDATE_ID|show CANDIDATE_ID
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from gupi.formation import store  # noqa: E402
from gupi.formation.rules_v2 import RulesV2  # noqa: E402
from gupi.memory import Memory  # noqa: E402
from gupi.records import Batch, Context, Observation, Source  # noqa: E402
from gupi.typedb.connection import connect  # noqa: E402

TEXT = "I think Alice Grey works at Acme Labs."
SAID = datetime(2025, 6, 1, 9, tzinfo=timezone.utc)


def main(database, phase, arg=None):
    driver = connect()
    try:
        memory = Memory(driver, database, packs=("core", "people"))
        if phase == "submit":
            src, ctx = Source("src:restart", "mail"), Context("ctx:restart", "conversation")
            obs = Observation(src.id, "m1", TEXT, SAID, ctx.id)
            memory.ingest(Batch(sources=(src,), observations=(obs,), contexts=(ctx,)))
            cset, _ = RulesV2().extract(obs)
            r = store.submit(memory, obs, cset)
            out = {"stored": r.stored, "outcomes": [d.outcome for d in r.decisions]}
        elif phase == "pending":
            out = {"pending": [s.candidate.id for s in store.pending(memory)]}
        elif phase == "approve":
            d = store.review(memory, arg, "approve", "reviewer-a", "checked with the team")
            out = {"outcome": d.outcome, "decided_by": d.decided_by}
        else:
            s = store.get(memory, arg)
            out = {"status": s.status, "claim": s.claim_id, "decisions": [(d.outcome, d.decided_by) for d in s.decisions],
                   "payload": s.payload}
        print(json.dumps(out))
    finally:
        driver.close()


if __name__ == "__main__":
    main(*sys.argv[1:])
