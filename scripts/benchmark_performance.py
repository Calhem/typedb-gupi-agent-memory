"""Performance measurements on a deterministic synthetic memory (offline, disposable gupi-perf-* databases).

    uv run python -I scripts/benchmark_performance.py --people 100 200 > docs/evaluation/phase-4-performance.json

For each size: ingestion throughput, then median latencies of ask (closed questions), query (open role),
the review queue, conflicts, keyword search and two-hop exploration. The review queue and conflicts are
also timed the Phase 3 way (load every claim, compare in Python) for comparison, at small sizes only:
the Phase 3 queue compared all pairs of believed claims for every hypothesis, which grows with the cube
of the memory size and did not finish within 30 minutes at 6,000 claims. One run on one machine:
indicative, not a benchmark suite.
"""

import argparse
import json
import random
import statistics
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gupi import conflicts as conflict_rules  # noqa: E402
from gupi import identity, review  # noqa: E402
from gupi.memory import Memory  # noqa: E402
from gupi.query import Question  # noqa: E402
from gupi.records import Batch, Claim, Context, Evidence, Observation, Referent, Source  # noqa: E402
from gupi.status import Status  # noqa: E402
from gupi.temporal import ValidTime  # noqa: E402
from gupi.typedb.connection import connect  # noqa: E402

START = datetime(2024, 1, 1, tzinfo=timezone.utc)


class Clock:
    now = START

    def __call__(self):
        return self.now


def world(people, seed=7):
    """People report to managers and work at organisations; some spells end; a few claims disagree."""
    rnd = random.Random(seed)
    orgs = [Referent(f"o:{i}", "organization", f"Org {i}") for i in range(max(2, people // 10))]
    persons = [Referent(f"p:{i}", "person", f"Person {i}") for i in range(people)]
    source = Source("src:perf", "document")
    items = []  # (observation, claim, decision)
    for i, p in enumerate(persons):
        day = START + timedelta(days=rnd.randrange(300))
        for kind in ("employment", "reporting", "reporting"):
            text = f"{kind} statement {i}-{len(items)}"
            obs = Observation(source.id, text, text, day, "ctx:perf")
            start = day - timedelta(days=rnd.randrange(400))
            end = (day + timedelta(days=rnd.randrange(1, 200))) if rnd.random() < 0.3 else None
            valid = ValidTime(start, start, end, end) if end else ValidTime(start, start, to_earliest=day)
            if kind == "employment":
                roles = {"employee": p.id, "employer": rnd.choice(orgs).id}
                values = {"job-title": rnd.choice(["Engineer", "Manager", "Analyst"])}
            else:
                roles = {"report": p.id, "manager": rnd.choice(persons).id}
                values = {}
            claim = Claim(kind, roles, (Evidence(obs.id),), valid, values=values,
                          valid_to_basis="stated" if end else "ongoing-at-observation")
            decision = rnd.choices(["accepted", "rejected", None], weights=[8, 1, 1])[0]
            items.append((obs, claim, decision))
    return source, orgs + persons, items


def timed(fn, repeat):
    times = []
    result = None
    for _ in range(repeat):
        t0 = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - t0)
    return round(statistics.median(times), 4), result


def phase3_queue(memory, at):
    """The Phase 3 review queue: every claim into Python, every hypothesis compared with every believed claim."""
    claims = memory.all_claims()
    rules = conflict_rules.load_constraints(memory.packs)
    believed = [c for c in claims if c.status_at(at) is Status.ACCEPTED]
    groups = identity.equivalents([c for c in claims if c.type == "identity"], at)
    return review.queue(claims, at, lambda c: [x for x in conflict_rules.detect([c] + believed, rules, groups=groups)
                                                if c.id in x.claim_ids], limit=20)


def phase3_conflicts(memory, at):
    claims = memory.all_claims()
    believed = [c for c in claims if c.status_at(at) is Status.ACCEPTED]
    return conflict_rules.detect(believed, conflict_rules.load_constraints(memory.packs),
                                 include=(conflict_rules.CONTRADICTION, conflict_rules.DIFFERING))


def measure(people, driver, repeat, phase3_max_claims):
    source, referents, items = world(people)
    db = f"gupi-perf-{uuid.uuid4().hex[:8]}"
    clock = Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        clock.now = START + timedelta(days=400)
        memory.ingest(Batch((source,), contexts=(Context("ctx:perf", "document"),), referents=tuple(referents)))
        t0 = time.perf_counter()
        for i in range(0, len(items), 25):
            chunk = items[i:i + 25]
            memory.ingest(Batch(observations=tuple(o for o, _, _ in chunk), claims=tuple(c for _, c, _ in chunk)))
        ingest_s = time.perf_counter() - t0
        clock.now += timedelta(days=1)
        decided = [(c.id, d) for _, c, d in items if d]
        t0 = time.perf_counter()
        for i in range(0, len(decided), 100):
            memory.review_many(decided[i:i + 100], "perf")
        review_s = time.perf_counter() - t0
        clock.now += timedelta(days=1)
        at = clock.now
        rnd = random.Random(1)
        sample = rnd.sample([c for _, c, _ in items], 20)
        valid = START + timedelta(days=200)

        def asks():
            for c in sample:
                memory.ask(c.type, c.roles, valid)
        ask_s, _ = timed(asks, repeat)
        open_q = [Question("reporting", {"report": c.roles["report"], "manager": None}, valid)
                  for c in sample if c.type == "reporting"][:10]

        def queries():
            for q in open_q:
                memory.query(q)
        query_s, _ = timed(queries, repeat)
        queue_s, queue = timed(lambda: memory.review_queue(limit=20), repeat)
        compare = len(items) <= phase3_max_claims  # the Phase 3 queue grows with the cube of memory size
        old_queue_s, old_queue = timed(lambda: phase3_queue(memory, at), 1) if compare else (None, None)
        conflicts_s, found = timed(lambda: memory.conflicts(), repeat)
        old_conflicts_s, old_found = timed(lambda: phase3_conflicts(memory, at), 1) if compare else (None, None)
        search_s, _ = timed(lambda: memory.search("reporting statement 12"), repeat)
        explore_s, graph = timed(lambda: memory.explore(sample[0].roles.get("report") or sample[0].roles["employee"],
                                                        depth=2), repeat)
        same = None if not compare else (
            {(x.kind, x.claim_ids) for x in found} == {(x.kind, x.claim_ids) for x in old_found}
            and [i.claim.id for i in queue] == [i.claim.id for i in old_queue])
        print(f"done: {people} people, {len(items)} claims", file=sys.stderr, flush=True)
        return {
            "people": people, "claims": len(items), "observations": len(items),
            "ingest_seconds": round(ingest_s, 2), "claims_per_second": round(len(items) / ingest_s, 1),
            "review_seconds": round(review_s, 2), "decisions": len(decided),
            "median_seconds": {
                "ask x20": ask_s, "query open role x10": query_s,
                "review_queue(limit=20)": queue_s, "review_queue, Phase 3 way": old_queue_s,
                "conflicts()": conflicts_s, "conflicts, Phase 3 way": old_conflicts_s,
                "keyword search": search_s, "explore depth 2": explore_s,
            },
            "conflicts_found": len(found), "queue_items": len(queue), "explore_nodes": len(graph.nodes),
            "same_results_as_phase_3": same,
        }
    finally:
        driver.databases.get(db).delete()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--people", type=int, nargs="+", default=[100, 200])
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--phase3-max-claims", type=int, default=700,
                        help="time the Phase 3 approach only up to this many claims (it is cubic)")
    args = parser.parse_args()
    driver = connect()
    print(json.dumps({"server": str(driver.server_version()), "results": [measure(n, driver, args.repeat, args.phase3_max_claims) for n in args.people]},
                     indent=2))


if __name__ == "__main__":
    main()
