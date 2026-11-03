"""Run an offline evidence-retrieval benchmark.

    uv run python -I -m gupi.benchmarks --dataset locomo --split dev [--no-embeddings] [--json PATH]

Results are retrieval metrics only, not official LoCoMo or LongMemEval scores.
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone

from gupi.benchmarks import common, locomo, longmemeval
from gupi.memory import Memory
from gupi.typedb.connection import connect


class Clock:
    now = datetime(2020, 1, 1, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dataset", choices=["locomo", "longmemeval"], required=True)
    p.add_argument("--split", choices=["dev", "heldout"], required=True)
    p.add_argument("--systems", nargs="+", default=common.CONFIG["systems"])
    p.add_argument("--no-embeddings", action="store_true", help="offline mode without the embeddings extra")
    p.add_argument("--limit", type=int, help="only the first N questions (smoke tests)")
    p.add_argument("--embedding-subset", action="store_true",
                   help="LongMemEval held-out: only the pre-registered embedding subset (benchmarks/config.json)")
    p.add_argument("--keep", action="store_true", help="keep the database afterwards")
    p.add_argument("--json", help="write results here")
    args = p.parse_args(argv)

    driver = connect()
    db = f"gupi-bench-{args.dataset}-{args.split}-{int(time.time())}"
    clock = Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    timings = {}
    try:
        t0 = time.perf_counter()
        if args.dataset == "locomo":
            data = locomo.load(args.split)
            turn_ids, observations = locomo.ingest(memory, clock, data)
            timings["ingest_seconds"] = time.perf_counter() - t0
            t0 = time.perf_counter()
            from gupi.extraction.pipeline import extract
            from gupi.extraction.rules import RuleExtractor
            extracted = extract(memory, RuleExtractor(), observations)
            timings["rule_extraction_seconds"] = time.perf_counter() - t0
            timings["claims_extracted"] = len(extracted.claims)
            qs, missing = locomo.questions(data, turn_ids)
            timings["evidence_ids_not_found"] = missing
            contexts = sorted({c for q in qs for c in q.contexts})
            timings["observations"] = len(observations)
        else:
            data = longmemeval.load(args.split)
            if args.embedding_subset:
                wanted = set(next(a["embedding_subset"] for a in common.CONFIG["amendments"] if "embedding_subset" in a))
                data = [q for q in data if q["question_id"] in wanted]
            by_context = longmemeval.ingest(memory, clock, data)
            timings["ingest_seconds"] = time.perf_counter() - t0
            print(f"ingested {sum(map(len, by_context.values()))} turns", file=sys.stderr, flush=True)
            qs = longmemeval.questions(data, by_context)
            contexts = sorted(by_context)
            timings["observations"] = sum(map(len, by_context.values()))
        timings["contexts"] = len(contexts)
        if args.limit:
            qs = qs[:args.limit]
        embedder = None
        if not args.no_embeddings and any(x in args.systems for x in ("embedding", "hybrid", "hybrid-unfiltered")):
            from gupi import vectors
            from gupi.embedding import FastEmbedder
            t0 = time.perf_counter()
            embedder = FastEmbedder(common.CONFIG["embedding"]["model"])
            timings["embedder_load_seconds"] = time.perf_counter() - t0
            t0 = time.perf_counter()
            started = time.perf_counter()

            def progress(done, total):
                rate = done / (time.perf_counter() - started)
                print(f"embedded {done}/{total} ({rate:.1f}/s)", file=sys.stderr, flush=True)
            timings["embeddings_written"] = vectors.store(memory, embedder, contexts, progress=progress)
            timings["embedding_seconds"] = time.perf_counter() - t0
        timings["database_bytes"] = common.database_bytes(db)
        clock.now = datetime(2030, 1, 1, tzinfo=timezone.utc)
        t0 = time.perf_counter()
        rows = common.run_questions(memory, qs, args.systems, embedder)
        timings["retrieval_seconds"] = time.perf_counter() - t0
        timings["peak_python_rss_bytes"] = common.peak_rss_bytes()
        result = {
            "dataset": args.dataset, "split": args.split, "questions": len(qs), "systems": args.systems,
            "embedding_subset": args.embedding_subset,
            "embeddings": embedder is not None,
            "config_sha256": hashlib.sha256((common.ROOT / "benchmarks" / "config.json").read_bytes()).hexdigest(),
            "note": "Evidence retrieval only; not an official LoCoMo or LongMemEval score.",
            "timings": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in timings.items()},
            "summary": common.summarise(rows), "rows": rows,
        }
        for unit, systems in result["summary"].items():
            for system, s in systems.items():
                o = s["overall"]
                print(f"{args.dataset} {args.split} {unit:7} {system:10} R@5 {o['recall@5']:.3f}  R@10 {o['recall@10']:.3f}  "
                      f"hit@5 {o['hit@5']:.3f}  MRR {o['mrr']:.3f}  empty {s['empty_results']}  "
                      f"median {s['latency_seconds']['median']}s")
        print(json.dumps(result["timings"]))
        if args.json:
            with open(args.json, "w") as f:
                json.dump(result, f, indent=1, default=str)
    finally:
        if not args.keep:
            driver.databases.get(db).delete()


if __name__ == "__main__":
    main()
