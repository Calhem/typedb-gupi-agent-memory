"""Layer D operational probe: how the candidate store behaves as it grows. Synthetic load only, never scored
for accuracy: copies of the 32 D3 passages with every name given a per-copy suffix ("Mara Quist" ->
"Mara Quistab"), each copy in its own context. Measures submit time, pending() time, v2 query latency and
database size per step, and that resubmission writes nothing."""

import re
import time
from datetime import timedelta

from gupi.benchmarks.e2e import common
from gupi.formation import evaluation as e6b
from gupi.formation import store
from gupi.formation.rules_v2 import RulesV2
from gupi.memory import Memory
from gupi.records import Batch, Context, Observation, Referent, Source

NAMES = ("Mara Quist", "Teo Brandt", "Ilsa Moreno", "Dana Okoro", "Omar Siddiq", "Arnholt Systems", "Pellwick",
         "Ravi", "Mara", "Teo")


def _suffix(i):
    s = ""
    i += 26
    while i:
        i, r = divmod(i, 26)
        s = chr(97 + r) + s
    return s


def rename(text, i):
    sfx = _suffix(i)
    pattern = re.compile("|".join(re.escape(n) for n in sorted(NAMES, key=len, reverse=True)))
    return pattern.sub(lambda m: " ".join(w + sfx for w in m.group(0).split(" ")), text)


def run(driver, label, copies=31, step=4, queries=20):
    data = e6b.load()
    db, clock = common.database_name("scale"), common.Clock(common.utc(data["observed_at"]))
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    source, ex, steps = Source("src:scale", "synthetic"), RulesV2(), []
    try:
        submitted = []
        t_all = time.perf_counter()
        for i in range(copies):
            ctx = Context(f"ctx:scale:{i}", "conversation")
            author = f"p:scale:{i}"
            memory.ingest(Batch(referents=(Referent(author, "person", rename("Dana Okoro", i)),)))
            prior, t_ingest, t_extract, t_submit, n_obs = {}, 0.0, 0.0, 0.0, 0
            for p in data["passages"]:
                clock.now += timedelta(seconds=1)
                obs = Observation(source.id, f"{i}:{p['id']}", rename(p["text"], i), clock.now, ctx.id,
                                  author if p.get("author") else None)
                t0 = time.perf_counter()
                memory.ingest(Batch(sources=(source,), observations=(obs,), contexts=(ctx,)))
                t_ingest += time.perf_counter() - t0
                t0 = time.perf_counter()
                cset, _ = ex.extract(obs, prior=tuple(prior.get(p.get("thread"), [])) if p.get("thread") else ())
                t_extract += time.perf_counter() - t0
                if p.get("thread"):
                    prior.setdefault(p["thread"], []).append(cset)
                if cset.candidates:
                    t0 = time.perf_counter()
                    store.submit(memory, obs, cset)
                    t_submit += time.perf_counter() - t0
                    submitted.append((obs, cset))
                n_obs += 1
            if (i + 1) % step == 0 or i == copies - 1:
                t0 = time.perf_counter()
                waiting = store.pending(memory)
                t_pending = time.perf_counter() - t0
                lat = []
                for j in range(min(queries, i + 1)):
                    k = (j * 7919) % (i + 1)
                    t0 = time.perf_counter()
                    memory.query_by_name("employment", {"employee": rename("Mara Quist", k), "employer": rename("Pellwick", k)},
                                         common.utc("2025-07-01"), clock.now, None, "v2")
                    lat.append(time.perf_counter() - t0)
                c = common.counts(memory)
                steps.append({"copies": i + 1, "observations": c["observation"], "candidates": c["memory-candidate"],
                              "decisions": c["formation-decision"], "claims": c["claim"], "pending": len(waiting),
                              "pending_seconds": round(t_pending, 4), "query_latency": common.latency(lat),
                              "last_copy": {"ingest_s_per_obs": round(t_ingest / n_obs, 5),
                                            "extract_s_per_obs": round(t_extract / n_obs, 6),
                                            "submit_s_per_obs": round(t_submit / n_obs, 5)},
                              "database_bytes": common.size(memory)})
        total = time.perf_counter() - t_all
        before = common.counts(memory)
        clock.now += timedelta(seconds=1)
        t0 = time.perf_counter()
        for obs, cset in submitted[-32:]:
            store.submit(memory, obs, cset)
        resubmit = time.perf_counter() - t0
        after = common.counts(memory)
        return {"meta": common.meta(label, "operational probe (synthetic load)"), "steps": steps,
                "total_seconds": round(total, 2),
                "resubmission": {"submissions": len(submitted[-32:]), "seconds": round(resubmit, 3),
                                 "decisions_before": before["formation-decision"], "decisions_after": after["formation-decision"],
                                 "candidates_before": before["memory-candidate"], "candidates_after": after["memory-candidate"],
                                 "claims_before": before["claim"], "claims_after": after["claim"]},
                "note": "Synthetic renamed copies of D3: operational measurements only, no accuracy."}
    finally:
        driver.databases.get(db).delete()
