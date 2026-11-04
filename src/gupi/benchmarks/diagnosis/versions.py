"""rules:v2 versus rules:v2.1 on every frozen check (docs/evaluation/extractor-d1-d2/).

    uv run python -I -m gupi.benchmarks.diagnosis.versions --json docs/evaluation/extractor-d1-d2/comparison.json

Earlier results are never overwritten: each check is run for both versions now, side by side. Needs TypeDB
and .data/ (for the complete-dataset counts). No API calls. Dataset text is never written.
"""

import argparse
import json
import sys
import uuid
from collections import Counter
from datetime import timedelta

from gupi import retrieval_eval
from gupi.benchmarks.common import ROOT
from gupi.benchmarks.diagnosis import counts, sample
from gupi.benchmarks.diagnosis.classify import observation as sample_observation
from gupi.benchmarks.e2e import adversarial, common, pipeline, world
from gupi.extraction.contract import referent_id
from gupi.formation import evaluation as e6b, extractors, store
from gupi.formation.rules_v21 import reason_kind
from gupi.memory import Memory
from gupi.query import Question
from gupi.records import Batch, Context, Observation, Referent, Source
from gupi.typedb.connection import connect

VERSIONS = ("rules:v2", "rules:v2.1")
FIXTURES = ROOT / "tests" / "fixtures" / "diagnosis"


def frozen_6b(version):
    data = e6b.load()
    s = e6b.score(data, e6b.run(extractors.get(version), data))
    return {k: v for k, v in s.items() if k != "rows"}


def phase2(version):
    return {split: {k: v for k, v in e6b.score_conversations(split, e6b.rules_v2_claims(extractors.get(version))).items()}
            for split in ("heldout", "dev")}


def adversarial_cases(driver, version):
    """The 6C development cases through the store, as in Phase 6D, with the chosen extractor."""
    data = json.loads(adversarial.frozen.DATA.read_text())
    rows, totals = [], Counter()
    for case in data["cases"]:
        db, clock = f"gupi-ver-adv-{uuid.uuid4().hex[:8]}", adversarial.frozen.Clock()
        clock.now = adversarial.frozen.when("2025-01-01T00:00:00Z")
        memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
        try:
            authors = {m["author"] for m in case["messages"] if m.get("author")}
            if authors:
                memory.ingest(Batch(referents=tuple(Referent(adversarial.frozen.person(a), "person", a) for a in sorted(authors))))
            obs_key = {}
            for m in case["messages"]:
                ctx = Context(f"ctx:{case['id']}:{m.get('context', 'main')}", "conversation")
                src = Source(f"src:{case['id']}:{m.get('source', 'mail')}", m.get("source", "mail"))
                obs = Observation(src.id, m["key"], m["text"], adversarial.frozen.when(m["at"]), ctx.id,
                                  adversarial.frozen.person(m["author"]) if m.get("author") else None)
                clock.now = obs.observed_at
                memory.ingest(Batch(sources=(src,), observations=(obs,), contexts=(ctx,)))
                obs_key[obs.id] = m["key"]
                cset, _ = extractors.get(version).extract(obs)
                if cset.candidates:
                    sub = store.submit(memory, obs, cset)
                    if m["key"] in case.get("approve", ()):
                        clock.now = obs.observed_at + timedelta(seconds=1)
                        for cid in sub.stored:
                            if store.get(memory, cid).status == "review":
                                store.review(memory, cid, "approve", "reviewer-a")
            q = case["question"]
            ctx_id = f"ctx:{case['id']}:{q.get('context', 'main')}"
            roles = {r: referent_id(ctx_id, kind, name) for r, (kind, name) in q["roles"].items()}
            clock.now = max(adversarial.frozen.when(m["at"]) for m in case["messages"]) + timedelta(seconds=2)
            res = memory.query(Question(q["type"], roles, adversarial.frozen.when(q["at"]),
                                        adversarial.frozen.when(q["believed_at"]) if q.get("believed_at") else None, semantics="v2"))
            qual = res.qualification
            got = {"answer": res.answer.name, "standing": qual.standing, "qualifiers": sorted(qual.qualifiers),
                   "asserters": sorted(qual.originators), "independent": qual.independent,
                   "cited": sorted({obs_key.get(c.observation_id, "?") for c in res.citations}), "definitive": qual.definitive}
        finally:
            driver.databases.get(db).delete()
        checks, bad = adversarial.frozen.score(case, got)
        totals.update({m: int(ok) for m, ok in checks.items()})
        totals["unsupported_definitive"] += bad
        rows.append({"id": case["id"], "answer": got["answer"], "checks": checks})
    return {"cases": len(rows), "totals": dict(totals), "rows": rows}


def world_e2e(driver, version):
    """The Phase 4 world end to end through the store (the 6D gupi-e2e configuration) with the chosen extractor."""
    saved = pipeline.EXTRACTOR
    pipeline.EXTRACTOR = extractors.get(version)
    w, questions = retrieval_eval.load()
    db, clock = common.database_name("ver-world"), common.Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        key_of, trace, _, _ = world.build_e2e(memory, clock, w, True)
        s = world.score(questions, {q["id"]: world.gupi_answer(memory, common.public(q)) for q in questions}, key_of)
        return {"correct": s["correct"], "of": s["questions"], "unsupported_definitive": s["unsupported_definitive"],
                "answers": {r["id"]: r["got"] for r in s["rows"]},
                "candidates": sum(len(t["candidates"]) for t in trace.values())}
    finally:
        pipeline.EXTRACTOR = saved
        driver.databases.get(db).delete()


def phase4(semantics):
    """Phase 4 (gold claims and rules:v1, unaffected by rules:v2.x), compared with the committed results."""
    committed = json.loads((ROOT / "docs" / "evaluation" / f"retrieval-{semantics}.json").read_text())
    now = retrieval_eval.main.__globals__["run"]
    out = {}
    for config in ("gold", "rules"):
        r = now(config, semantics=semantics)
        old = next(x for x in committed if x["config"] == config)
        out[config] = {"structured_correct": r["structured"]["correct"], "keyword_correct": r["keyword"]["correct"],
                       "answers_identical_to_committed": [x["got"] for x in r["structured"]["rows"]] ==
                       [x["got"] for x in old["structured"]["rows"]]}
    return out


def probes(version):
    out = {}
    for name in ("probes-v1.json", "probes-v2.json"):
        data = json.loads((FIXTURES / name).read_text())
        rows = []
        for p in data["probes"]:
            ex, prior = extractors.get(version), []
            for n, text in enumerate(p.get("context", []) + [p["text"]]):
                o = Observation("src:p", f"{p['id']}-{n}", text, common.utc(data["said_at"]), "ctx:p", "p:author")
                cset, report = ex.extract(o, prior=tuple(prior))
                prior.append(cset)
            rows.append({"id": p["id"], "candidates": [{"type": c.claim_type, "roles": {x.role: x.surface for x in c.participants}}
                                                       for c in cset.candidates],
                         "rejection_kinds": sorted(reason_kind(r) for _, r in report.rejected)})
        out[name] = rows
    return out


def complete_counts(version, observations):
    ex, kinds, cands = extractors.get(version), Counter(), 0
    for o in observations:
        cset, report = ex.extract(o)
        cands += len(cset.candidates)
        kinds.update(reason_kind(r) for _, r in report.rejected)
    return {"turns": len(observations), "candidates": cands, "rejections_by_kind": dict(kinds)}


def sample_kinds(version, texts):
    s = json.loads(sample.OUT.read_text())
    out = {}
    for d, v in s["datasets"].items():
        for part in ("representative", "targeted"):
            kinds, cands = Counter(), 0
            for t in v[part]:
                cset, report = extractors.get(version).extract(sample_observation(d, t, texts[(d, t["key"])]))
                cands += len(cset.candidates)
                kinds.update(reason_kind(r) for _, r in report.rejected)
            out[f"{d}/{part}"] = {"candidates": cands, "rejections_by_kind": dict(kinds)}
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json")
    args = p.parse_args(argv)
    driver = connect()
    lo, lme = counts.locomo_all(), counts.longmemeval_all()
    texts = sample.texts()
    result = {"meta": {**common.meta("versions", "rules:v2 vs rules:v2.1"), "phase": "D1/D2"},
              "phase4": {s: phase4(s) for s in ("v1", "v2")}, "versions": {}}
    for v in VERSIONS:
        result["versions"][v] = {
            "frozen_6b": frozen_6b(v), "phase2": phase2(v), "adversarial_6c": adversarial_cases(driver, v),
            "world_e2e": world_e2e(driver, v), "probes": probes(v),
            "complete_datasets": {"locomo": complete_counts(v, lo), "longmemeval": complete_counts(v, lme)},
            "phase7a_sample": sample_kinds(v, texts)}
        print(v, "done", flush=True)
    a, b = (result["versions"][v] for v in VERSIONS)
    result["differences"] = {
        "frozen_6b_identical": a["frozen_6b"] == b["frozen_6b"], "phase2_identical": a["phase2"] == b["phase2"],
        "adversarial_identical": a["adversarial_6c"] == b["adversarial_6c"], "world_identical": a["world_e2e"] == b["world_e2e"],
        "probe_candidates_changed": [(name, x["id"], x["candidates"], y["candidates"])
                                     for name in a["probes"] for x, y in zip(a["probes"][name], b["probes"][name])
                                     if x["candidates"] != y["candidates"]],
        "probe_rejections_changed": sum(x["rejection_kinds"] != y["rejection_kinds"]
                                        for name in a["probes"] for x, y in zip(a["probes"][name], b["probes"][name])),
        "complete_dataset_candidates": {d: (a["complete_datasets"][d]["candidates"], b["complete_datasets"][d]["candidates"])
                                        for d in ("locomo", "longmemeval")}}
    if args.json:
        open(args.json, "w").write(json.dumps(result, indent=1, default=str) + "\n")
    print(json.dumps({"phase4": result["phase4"], "differences": result["differences"],
                      "complete": {v: result["versions"][v]["complete_datasets"] for v in VERSIONS},
                      "sample": {v: result["versions"][v]["phase7a_sample"] for v in VERSIONS},
                      "6b": {v: (result["versions"][v]["frozen_6b"]["precision"], result["versions"][v]["frozen_6b"]["recall"]) for v in VERSIONS},
                      "adv": {v: result["versions"][v]["adversarial_6c"]["totals"] for v in VERSIONS},
                      "world": {v: result["versions"][v]["world_e2e"]["correct"] for v in VERSIONS}}, indent=1, default=str))


if __name__ == "__main__":
    sys.exit(main())
