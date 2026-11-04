"""D4: the 17 development-only adversarial cases, through the candidate store instead of form().

Identical to scripts/evaluate_adversarial.run_case except for formation: candidates are submitted with
`store.submit`, and a case's reviewer approvals are `store.review(approve)` on its pending candidates one
second after submission. Scored with the frozen `score` of that script. Development tests only.
"""

import importlib.util
import time
import uuid
from datetime import timedelta

from gupi.benchmarks.common import ROOT
from gupi.benchmarks.e2e import common
from gupi.extraction.contract import referent_id
from gupi.formation import store
from gupi.formation.rules_v2 import RulesV2
from gupi.memory import Memory
from gupi.query import Question
from gupi.records import Batch, Context, Observation, Referent, Source

_spec = importlib.util.spec_from_file_location("evaluate_adversarial", ROOT / "scripts" / "evaluate_adversarial.py")
frozen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(frozen)


def run_case(driver, case):
    db, clock = f"gupi-6d-adv-{uuid.uuid4().hex[:8]}", frozen.Clock()
    clock.now = frozen.when("2025-01-01T00:00:00Z")
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    outcomes = []
    try:
        authors = {m["author"] for m in case["messages"] if m.get("author")}
        if authors:
            memory.ingest(Batch(referents=tuple(Referent(frozen.person(a), "person", a) for a in sorted(authors))))
        obs_key = {}
        for m in case["messages"]:
            ctx = Context(f"ctx:{case['id']}:{m.get('context', 'main')}", "conversation")
            src = Source(f"src:{case['id']}:{m.get('source', 'mail')}", m.get("source", "mail"))
            obs = Observation(src.id, m["key"], m["text"], frozen.when(m["at"]), ctx.id,
                              frozen.person(m["author"]) if m.get("author") else None)
            clock.now = obs.observed_at
            memory.ingest(Batch(sources=(src,), observations=(obs,), contexts=(ctx,)))
            obs_key[obs.id] = m["key"]
            cset, _ = RulesV2().extract(obs)
            if cset.candidates:
                sub = store.submit(memory, obs, cset)
                if m["key"] in case.get("approve", ()):
                    clock.now = obs.observed_at + timedelta(seconds=1)
                    for cid in sub.stored:
                        if store.get(memory, cid).status == "review":
                            store.review(memory, cid, "approve", "reviewer-a")
                outcomes += [(m["key"], store.get(memory, cid).status) for cid in sub.stored]
        q = case["question"]
        ctx_id = f"ctx:{case['id']}:{q.get('context', 'main')}"
        roles = {r: referent_id(ctx_id, kind, name) for r, (kind, name) in q["roles"].items()}
        clock.now = max(frozen.when(m["at"]) for m in case["messages"]) + timedelta(seconds=2)
        t0 = time.perf_counter()
        res = memory.query(Question(q["type"], roles, frozen.when(q["at"]),
                                    frozen.when(q["believed_at"]) if q.get("believed_at") else None, semantics="v2"))
        seconds = time.perf_counter() - t0
        qual = res.qualification
        counts = common.counts(memory)
        return {"answer": res.answer.name, "standing": qual.standing, "qualifiers": sorted(qual.qualifiers),
                "asserters": sorted(qual.originators), "independent": qual.independent,
                "cited": sorted({obs_key.get(c.observation_id, "?") for c in res.citations}),
                "definitive": qual.definitive, "explanation": qual.explanation,
                "candidate_outcomes": outcomes, "seconds": seconds,
                "store_used": counts["memory-candidate"] > 0,
                "claims_without_store_link": counts["claims_with_candidate_but_no_store_link"]}
    finally:
        driver.databases.get(db).delete()


def run(driver, label):
    import json
    data = json.loads(frozen.DATA.read_text())
    rows, totals, unsupported, withheld = [], {m: 0 for m in frozen.MEASURES}, 0, 0
    for case in data["cases"]:
        got = run_case(driver, case)
        checks, bad = frozen.score(case, got)
        for m, ok in checks.items():
            totals[m] += ok
        unsupported += bad
        withheld += case["expect"]["definitive"] and not got["definitive"]
        rows.append({"id": case["id"], "about": case["about"], "expected": case["expect"], "got": got,
                     "checks": checks, "unsupported_definitive": bad})
    n = len(data["cases"])
    return {"meta": common.meta(label, "D4 adversarial (development tests, via the candidate store)"),
            "summary": {"cases": n, **{m: f"{totals[m]}/{n}" for m in frozen.MEASURES},
                        "unsupported_definitive": f"{unsupported}/{n}",
                        "definitive_withheld_where_warranted": f"{withheld}/{sum(c['expect']['definitive'] for c in data['cases'])}",
                        "latency": common.latency([r["got"]["seconds"] for r in rows])},
            "rows": rows, "note": "Development tests written by the qualification's designer: not independent evidence."}
