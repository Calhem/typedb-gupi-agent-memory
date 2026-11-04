"""Phase 7A section 7: an independent reproduction of candidate counts.

    uv run python -I -m gupi.benchmarks.diagnosis.counts --json docs/evaluation/phase-7a/counts.json

Written separately from the Phase 6D runner: it rebuilds observations with the adapters' rules, calls
RulesV2.extract directly, separates raw candidates (kept plus those the extractor's own validation
rejected), and submits any kept candidate to a fresh candidate store to count the policy's decisions.
- Deterministic subset: turns with sha256("phase7a-counts-v1|<dataset>|<key>") mod 20 == 0 (about 5%).
- Complete datasets: every turn of LoCoMo (10 conversations) and LongMemEval S (all 500 questions).
No retrieval or embedding is run. No text is written.
"""

import argparse
import hashlib
import json
import sys
import uuid
from datetime import timedelta

from gupi.benchmarks import longmemeval
from gupi.benchmarks.diagnosis.audit import NO_PATTERN, locomo_adapter
from gupi.benchmarks.e2e import common
from gupi.formation import store
from gupi.formation.rules_v2 import RulesV2
from gupi.memory import Memory
from gupi.records import Batch, Context, Observation, Referent, Source
from gupi.typedb.connection import connect

SEED = "phase7a-counts-v1"


def in_subset(dataset, key):
    return int(hashlib.sha256(f"{SEED}|{dataset}|{key}".encode()).hexdigest(), 16) % 20 == 0


def locomo_all():
    import json as j
    from gupi.benchmarks.locomo import PATH
    return [o for _, o, _ in locomo_adapter(j.loads(PATH.read_text()))]


def longmemeval_all():
    data = json.loads(longmemeval.PATH.read_text())
    versions = {}
    for q in data:
        for sid, date, turns in zip(q["haystack_session_ids"], q["haystack_dates"], q["haystack_sessions"]):
            versions.setdefault(longmemeval.context_id(sid, date, turns), (sid, date, turns))
    out = []
    for cid, (sid, date, turns) in sorted(versions.items()):
        when = longmemeval.parse_date(date)
        out += [Observation(longmemeval.SOURCE.id, f"{cid}:{i}", t["content"], when + timedelta(seconds=i), cid,
                            author_id=longmemeval.ROLES[t["role"]].id) for i, t in enumerate(turns)]
    return out


def count(driver, observations):
    ex = RulesV2()
    c = {"turns_examined": len(observations), "turns_passed_to_extractor": 0, "raw_candidates": 0,
         "passing_validation": 0, "rejected_by_validation": 0, "unparsed_in_domain_clauses": 0,
         "stored": 0, "formed": 0, "withheld": 0, "review": 0, "rejected_by_policy": 0, "exceptions": 0}
    kept = []
    for o in observations:
        c["turns_passed_to_extractor"] += 1
        try:
            cset, report = ex.extract(o)
        except Exception:  # counted, never hidden
            c["exceptions"] += 1
            continue
        invalid = [r for r in report.rejected if not r[1].startswith(NO_PATTERN)]
        c["unparsed_in_domain_clauses"] += len(report.rejected) - len(invalid)
        c["rejected_by_validation"] += len(invalid)
        c["passing_validation"] += len(cset.candidates)
        c["raw_candidates"] += len(cset.candidates) + len(invalid)
        if cset.candidates:
            kept.append((o, cset))
    if kept:
        db, clock = f"gupi-7a-counts-{uuid.uuid4().hex[:8]}", common.Clock()
        memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
        try:
            for o, cset in kept:
                clock.now = o.observed_at + timedelta(minutes=30)
                memory.ingest(Batch((Source(o.source_id, "conversation"),), (o,),
                                    (Referent(o.author_id, "person", "author"),) if o.author_id else (),
                                    contexts=(Context(o.context_id, "session"),)))
                for cid in store.submit(memory, o, cset).stored:
                    status = store.get(memory, cid).status
                    c["stored"] += 1
                    c["rejected_by_policy" if status == "rejected" else status] += 1
        finally:
            driver.databases.get(db).delete()
    return c


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json")
    args = p.parse_args(argv)
    driver = connect()
    result = {"meta": {**common.meta("counts", "Phase 7A independent counts"), "phase": "7A"}, "subset_rule": f"sha256('{SEED}|<dataset>|<key>') mod 20 == 0"}
    for name, obs in (("locomo", locomo_all()), ("longmemeval", longmemeval_all())):
        result[name] = {"subset": count(driver, [o for o in obs if in_subset(name, o.record_key)]),
                        "complete": count(driver, obs)}
    if args.json:
        open(args.json, "w").write(json.dumps(result, indent=1, default=str) + "\n")
    print(json.dumps(result, indent=1, default=str))


if __name__ == "__main__":
    sys.exit(main())
