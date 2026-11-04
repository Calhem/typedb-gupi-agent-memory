"""Phase 7A controlled extraction probes (tests/fixtures/diagnosis/probes-v1.json), each in its own database.

    uv run python -I -m gupi.benchmarks.diagnosis.probes --json docs/evaluation/phase-7a/probes-first-run.json

Each probe's context messages and then the probe itself are ingested, extracted by rules:v2 (with earlier
sets in the thread as prior) and submitted to the candidate store. Recorded: the candidates, what the store
decided, the claims formed and the believed claims, and whether the result matches the expectation.
"""

import argparse
import json
import sys
import uuid
from datetime import timedelta

from gupi.benchmarks.common import ROOT
from gupi.benchmarks.diagnosis.audit import NO_PATTERN, why_no_pattern
from gupi.benchmarks.e2e import common
from gupi.formation import store
from gupi.formation.rules_v2 import RulesV2
from gupi.memory import Memory
from gupi.records import Batch, Context, Observation, Referent, Source
from gupi.typedb.connection import connect

DATA = ROOT / "tests" / "fixtures" / "diagnosis" / "probes-v1.json"
AUTHOR = "p:ivo-marsh"


def run_probe(driver, data, probe):
    db, clock = f"gupi-7a-probe-{uuid.uuid4().hex[:8]}", common.Clock(common.utc(data["said_at"]))
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    src, ctx = Source("src:probe", "chat"), Context(f"ctx:{probe['id']}", "conversation")
    ex, prior, out = RulesV2(), [], None
    try:
        memory.ingest(Batch(referents=(Referent(AUTHOR, "person", data["author"]),)))
        messages = list(probe.get("context", [])) + [probe["text"]]
        for n, text in enumerate(messages):
            clock.now += timedelta(minutes=1)
            obs = Observation(src.id, f"{probe['id']}-{n}", text, clock.now, ctx.id, AUTHOR)
            memory.ingest(Batch(sources=(src,), observations=(obs,), contexts=(ctx,)))
            cset, report = ex.extract(obs, prior=tuple(prior))
            prior.append(cset)
            clock.now += timedelta(seconds=1)
            sub = store.submit(memory, obs, cset) if cset.candidates else None
            if n == len(messages) - 1:
                cands = []
                for c in cset.candidates:
                    s = store.get(memory, c.id)
                    cands.append({"type": c.claim_type, "roles": {p.role: p.surface for p in c.participants},
                                  "times": [(t.kind, t.phrase, t.earliest and t.earliest.date().isoformat(),
                                             t.latest and t.latest.date().isoformat()) for t in c.times],
                                  "polarity": c.polarity, "modality": c.modality, "commitment": c.commitment,
                                  "relations": [r.kind + ("" if r.target == "?" else ":named") for r in c.relations],
                                  "status": s.status if s else None,
                                  "reason": s.decisions[-1].reason if s and s.decisions else None,
                                  "claim_believed": bool(s and s.claim_id and s.claim_id in memory.believed_ids(clock.now))})
                out = {"candidates": cands, "invalid": len(sub.invalid) if sub else 0,
                       "not_extracted": [why_no_pattern(r[0]) if r[1].startswith(NO_PATTERN) else r[1] for r in report.rejected],
                       "notes": list(report.notes)}
        return out
    finally:
        driver.databases.get(db).delete()


def judge(probe, got):
    exp = probe["expect"]
    if exp is None:
        return "correct: nothing extracted" if not got["candidates"] else "wrong: extracted where nothing should be"
    t, roles, kind = exp
    for c in got["candidates"]:
        if c["type"] == t and {r: s.casefold() for r, s in c["roles"].items()} == {r: s.casefold() for r, s in roles.items()}:
            kinds = [k for k, *_ in c["times"]]
            return "match" if kind in kinds else f"match, but time kind {kinds} (expected {kind})"
    if got["candidates"]:
        return "wrong participants or type"
    return "missed"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json")
    args = p.parse_args(argv)
    data = json.loads(DATA.read_text())
    driver = connect()
    rows = []
    for probe in data["probes"]:
        got = run_probe(driver, data, probe)
        rows.append({"id": probe["id"], "proposition": probe["p"], "variation": probe["variation"], "text": probe["text"],
                     "context": probe.get("context", []), "expect": probe["expect"], "verdict": judge(probe, got), **got})
    summary = {}
    for r in rows:
        v = r["verdict"].split(",")[0]
        summary.setdefault(r["proposition"], {}).setdefault(v, 0)
        summary[r["proposition"]][v] += 1
    result = {"meta": {**common.meta("probes", "Phase 7A probes"), "phase": "7A"}, "probes": len(rows),
              "verdicts": {v: sum(r["verdict"].split(",")[0] == v for r in rows) for v in sorted({r["verdict"].split(",")[0] for r in rows})},
              "by_proposition": summary, "rows": rows}
    if args.json:
        open(args.json, "w").write(json.dumps(result, indent=1, default=str) + "\n")
    for r in rows:
        print(f"{r['id']:6} {r['verdict'][:48]:48} {[(c['roles'], c['status']) for c in r['candidates']]} {r['not_extracted']}")
    print(json.dumps({k: result[k] for k in ("probes", "verdicts", "by_proposition")}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
