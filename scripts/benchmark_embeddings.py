"""Embedding benchmarks: generation speed, storage in TypeDB, retrieval latency and exact-search scaling.

    uv run --extra embeddings python -I scripts/benchmark_embeddings.py > docs/evaluation/phase-5/embeddings.json

Generation uses the real local model on sample texts of three lengths. Scaling uses deterministic random
384-dimensional vectors stored in TypeDB (so it does not need hours of embedding), searched exactly with the
pure-Python ExactCosine and with NumpyCosine. One run on one machine: indicative only.
"""

import json
import random
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from typedb.driver import TransactionType  # noqa: E402

from gupi import embedding, ids, typeql, vectors  # noqa: E402
from gupi.benchmarks.common import database_bytes  # noqa: E402
from gupi.memory import Memory  # noqa: E402
from gupi.records import Batch, Context, Observation, Source  # noqa: E402
from gupi.typedb.connection import connect, transaction  # noqa: E402

SIZES = [1_000, 5_000, 20_000, 50_000]
DIM = 384
SOURCE = Source("src:bench", "document")
WHEN = datetime(2025, 1, 1, tzinfo=timezone.utc)


def generation():
    model = embedding.FastEmbedder()
    out = {"model": model.model, "dimension": model.dimension}
    for label, words in (("short (10 words)", 10), ("medium (80 words)", 80), ("long (400 words)", 400)):
        texts = [" ".join(f"word{(i * 7 + j) % 997}" for j in range(words)) for i in range(256)]
        model.embed(texts[:8])  # warm up
        t0 = time.perf_counter()
        model.embed(texts)
        out[label] = {"texts_per_second": round(len(texts) / (time.perf_counter() - t0), 1)}
    vec = model.embed(["a sentence"])[0]
    out["stored_vector_chars"] = len(embedding.encode(vec))
    return out


def scaling(driver):
    rnd = random.Random(3)
    db = f"gupi-embbench-{uuid.uuid4().hex[:8]}"
    memory = Memory.open(db, packs=("core",), driver=driver, create=True)
    results, done = [], 0
    try:
        ctx = Context("ctx:vectors", "document")
        memory.ingest(Batch((SOURCE,), contexts=(ctx,)))
        for size in SIZES:
            t0 = time.perf_counter()
            for start in range(done, size, 1000):
                n = min(1000, size - start)
                obs = tuple(Observation(SOURCE.id, f"o{i}", f"text {i}", WHEN, ctx.id) for i in range(start, start + n))
                memory.ingest(Batch(observations=obs))
                rows = [{"oid": o.id, "eid": ids.stable_id("embedding", "random", o.id),
                         "v": embedding.encode([rnd.gauss(0, 1) for _ in range(DIM)]), "m": "random", "d": DIM} for o in obs]
                with transaction(memory.driver, memory.database, TransactionType.WRITE) as tx:
                    typeql.run_rows(tx, """match $o isa observation, has gupi-id == $oid;
                        insert $e isa embedding, has gupi-id == $eid, has embedding-vector == $v, has embedding-model == $m,
                               has embedding-dim == $d; embedding-of (vector: $e, target: $o);""", rows)
            write_s = time.perf_counter() - t0
            added = size - done
            done = size
            query = [rnd.gauss(0, 1) for _ in range(DIM)]
            fetch, python, numpy_ = [], [], []
            for _ in range(3):
                t0 = time.perf_counter()
                with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
                    cands = sorted(vectors.vectors_in(tx, [ctx.id], "random").items())
                fetch.append(time.perf_counter() - t0)
                t0 = time.perf_counter()
                top_np = embedding.NumpyCosine().search(query, cands, 10)
                numpy_.append(time.perf_counter() - t0)
            t0 = time.perf_counter()
            top_py = embedding.ExactCosine().search(query, cands, 10)
            python.append(time.perf_counter() - t0)
            results.append({
                "vectors": size, "write_vectors_per_second": round(added / write_s, 1),
                "fetch_from_typedb_seconds": round(statistics.median(fetch), 3),
                "numpy_cosine_seconds": round(statistics.median(numpy_), 4),
                "pure_python_cosine_seconds": round(python[0], 3),
                "same_top10": [i for i, _ in top_np] == [i for i, _ in top_py],
                "database_bytes": database_bytes(db),
            })
            print(f"done {size}", file=sys.stderr, flush=True)
    finally:
        driver.databases.get(db).delete()
    return results


def main():
    driver = connect()
    print(json.dumps({"server": str(driver.server_version()), "generation": generation(), "scaling": scaling(driver)}, indent=2))


if __name__ == "__main__":
    main()
