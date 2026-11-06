"""Phase 8B development evaluation: keyword against keyword plus conversational structure, same budget.

    uv run python -I -m gupi.benchmarks.phase8 --dataset locomo --json PATH

Development splits only, by construction: there is no option to read held-out data. Evidence retrieval only: these
are not LoCoMo, LongMemEval or Agent Memory Leaderboard results.
"""

import argparse
import hashlib
import json
import statistics
import time
from datetime import datetime, timezone

from gupi import evidence, paths
from gupi.benchmarks import common, locomo, longmemeval
from gupi.benchmarks.__main__ import Clock
from gupi.memory import Memory
from gupi.typedb.connection import connect

CONFIG_PATH = common.ROOT / "benchmarks" / "phase8b.json"
CONFIG = json.loads(CONFIG_PATH.read_text())
SPLIT = "dev"


def score(ranked, baseline, gold):
    out = {}
    for k in CONFIG["k"]:
        top, base = set(ranked[:k]), set(baseline[:k])
        out[f"recall@{k}"] = len(top & gold) / len(gold)
        out[f"precision@{k}"] = len(top & gold) / k
        out[f"added@{k}"] = len((top - base) & gold)
        out[f"displaced@{k}"] = len((base - top) & gold)
    return out


def rank(memory, q, system):
    pool = CONFIG["pool"]
    if system == "keyword":
        return evidence.keyword(memory, q.text, q.contexts, pool).ids
    budget = paths.Budget(k=pool, pool=pool, **CONFIG["budget"])
    if system == "claim-paths":                    # with no claims this should equal conversational, at some cost
        return paths.retrieve(memory, q.text, q.contexts, budget).ids
    return paths.conversational(memory, q.text, q.contexts, budget).ids


def run(memory, questions, systems):
    rows = []
    for q in questions:
        baseline = None
        for system in systems:
            t0 = time.perf_counter()
            ranked = rank(memory, q, system)
            seconds = time.perf_counter() - t0
            baseline = ranked if baseline is None else baseline
            for unit, gold in q.gold.items():
                if gold:
                    r = ranked if unit == "turn" else common.rank_units(ranked, q.unit_of[unit])
                    b = baseline if unit == "turn" else common.rank_units(baseline, q.unit_of[unit])
                    rows.append({"question": q.id, "category": q.category, "system": system, "unit": unit,
                                 "seconds": seconds, **score(r, b, gold)})
    return rows


def summarise(rows):
    out = {}
    for unit in sorted({r["unit"] for r in rows}):
        for system in sorted({r["system"] for r in rows}):
            sel = [r for r in rows if r["unit"] == unit and r["system"] == system]
            keys = [k for k in sel[0] if "@" in k]

            def mean(rs):
                return {k: round(statistics.mean(r[k] for r in rs), 4) for k in keys} | {"questions": len(rs)}
            secs = sorted(r["seconds"] for r in sel)
            out.setdefault(unit, {})[system] = {
                "overall": mean(sel), "by_category": {c: mean([r for r in sel if r["category"] == c])
                                                      for c in sorted({r["category"] for r in sel})},
                "latency_seconds": {"p50": round(secs[len(secs) // 2], 4), "p95": round(secs[int(len(secs) * .95)], 4)}}
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dataset", choices=["locomo", "longmemeval"], required=True)
    p.add_argument("--systems", nargs="+", default=CONFIG["systems"])
    p.add_argument("--json", help="write results here")
    args = p.parse_args(argv)
    driver = connect()
    db, clock, info = f"gupi-bench-phase8-{args.dataset}-{int(time.time())}", Clock(), {}
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        if args.dataset == "locomo":
            data = locomo.load(SPLIT)
            turn_ids, observations = locomo.ingest(memory, clock, data)
            from gupi.extraction.pipeline import extract
            from gupi.extraction.rules import RuleExtractor
            info["claims_extracted"] = len(extract(memory, RuleExtractor(), observations).claims)
            questions, _ = locomo.questions(data, turn_ids)
            info["observations"] = len(observations)
        else:
            data = longmemeval.load(SPLIT)
            by_context = longmemeval.ingest(memory, clock, data)
            questions = longmemeval.questions(data, by_context)
            info["observations"] = sum(map(len, by_context.values()))
        clock.now = datetime(2030, 1, 1, tzinfo=timezone.utc)
        rows = run(memory, questions, args.systems)
        result = {"dataset": args.dataset, "split": SPLIT, "questions": len(questions), "info": info,
                  "config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
                  "note": "Evidence retrieval on development data only; not a benchmark or leaderboard score.",
                  "summary": summarise(rows), "rows": rows}
        for unit, systems in result["summary"].items():
            for system, s in systems.items():
                o = s["overall"]
                print(f"{args.dataset} {unit:7} {system:14} R@5 {o['recall@5']:.3f} R@10 {o['recall@10']:.3f} "
                      f"R@50 {o['recall@50']:.3f} p50 {s['latency_seconds']['p50']}s p95 {s['latency_seconds']['p95']}s")
        if args.json:
            with open(args.json, "w") as f:
                json.dump(result, f, indent=1, default=str)
    finally:
        driver.databases.get(db).delete()


if __name__ == "__main__":
    main()
