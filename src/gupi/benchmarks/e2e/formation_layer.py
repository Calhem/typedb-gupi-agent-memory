"""Layer A on D2 (Phase 2 held-out conversations) and D3 (the frozen 6B set), through the candidate store
into TypeDB. No reviewer: what is reported is what the policy alone did."""

import json
import time
from datetime import timedelta

from gupi.benchmarks.e2e import common, pipeline
from gupi.benchmarks.e2e.world import gold_vt
from gupi.extraction.contract import normalise
from gupi.formation import evaluation as e6b
from gupi.formation import store
from gupi.formation.rules_v2 import RulesV2
from gupi.memory import Memory
from gupi.records import Batch, Context, Observation, Referent, Source

PHASE2 = e6b.CONVERSATIONS / "heldout"


def _match(cands, gold):
    """One-to-one greedy matching by claim type and role surfaces (gold order)."""
    free, pairs, misses = list(range(len(cands))), [], []
    for g in gold:
        j = next((j for j in free if cands[j]["type"] == g["type"] and set(cands[j]["roles"]) == set(g["roles"])
                  and all(normalise(cands[j]["roles"][r]) == normalise(n) for r, n in g["roles"].items())), None)
        if j is None:
            misses.append(g)
        else:
            free.remove(j)
            pairs.append((g, cands[j]))
    return pairs, misses, [cands[j] for j in free]


def phase2(driver, label):
    """D2: every held-out message ingested, extracted, submitted; gold claims and mentions compared."""
    db, clock = common.database_name("d2"), common.Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    timings, rows, all_ids = {}, [], []
    tot = {"expected": 0, "extracted": 0, "matched": 0, "role_assignment_correct": 0,
           "mentions_gold": 0, "mentions_extracted": 0, "mentions_matched": 0,
           "start_correct": 0, "end_correct": 0, "both_correct": 0, "time_scored": 0,
           "accepted_claim": 0, "candidate_only": 0, "absent": 0}
    try:
        for path in sorted(PHASE2.glob("*.json")):
            conv = json.loads(path.read_text())
            source, ctx = Source("src:" + conv["id"], "conversation"), Context("ctx:" + conv["id"], "conversation")
            prior = []
            for m in conv["messages"]:
                said = common.utc(m["at"])
                obs = Observation(source.id, m["key"], m["text"], said, ctx.id)
                cset, report, sub = pipeline.ingest_extract_submit(
                    memory, clock, obs, Batch(sources=(source,), observations=(obs,), contexts=(ctx,)), prior,
                    received=said + timedelta(hours=1), timings=timings)
                prior.append(cset)
                cands = [pipeline.summary(c) for c in cset.candidates]
                all_ids += [c["id"] for c in cands]
                gold = [g for g in conv["gold"]["claims"] if g["message"] == m["key"]]
                pairs, misses, extra = _match(cands, gold)
                # entities: candidate participant surfaces against gold mentions of this message
                gm = sorted(normalise(x["text"]) for x in conv["gold"]["mentions"] if x["message"] == m["key"])
                em = sorted({normalise(s) for c in cands for s in c["roles"].values()})
                tot["mentions_gold"] += len(gm)
                tot["mentions_extracted"] += len(em)
                tot["mentions_matched"] += len(set(gm) & set(em))
                tot["expected"] += len(gold)
                tot["extracted"] += len(cands)
                tot["matched"] += len(pairs)
                pair_rows = []
                for g, c in pairs:
                    state = pipeline.stored_state(memory, c["id"])
                    vt, why = pipeline.mapped_time(_cand(memory, c["id"]))
                    got = [x.isoformat() if x else None for x in (vt.from_earliest, vt.from_latest, vt.to_earliest, vt.to_latest)] if vt else None
                    want = gold_vt(g, said)
                    start_ok = bool(got) and got[:2] == want[:2]
                    end_ok = bool(got) and got[2:] == want[2:]
                    tot["role_assignment_correct"] += 1  # matched implies the roles are right
                    tot["time_scored"] += 1
                    tot["start_correct"] += start_ok
                    tot["end_correct"] += end_ok
                    tot["both_correct"] += start_ok and end_ok
                    formed = state.get("status") == "formed" and pipeline.believed(memory, state.get("claim"), clock.now)
                    tot["accepted_claim" if formed else "candidate_only"] += 1
                    pair_rows.append({"gold": g, "candidate": c, "state": state, "valid_time": got, "gold_valid_time": want,
                                      "unmappable": why, "start_ok": start_ok, "end_ok": end_ok})
                tot["absent"] += len(misses)
                rows.append({"message": m["key"], "text": m["text"], "pairs": pair_rows, "missed": misses,
                             "extra": extra, "not_extracted": [list(r) for r in report.rejected]})
        result = {"meta": common.meta(label, "D2 Phase 2 held-out"), "totals": tot,
                  "policy_outcomes": pipeline.first_decisions(memory, all_ids),
                  "final_outcomes": pipeline.outcome_counts(memory, all_ids),
                  "database": {**common.counts(memory), "bytes": common.size(memory)},
                  "timings": {k: round(v, 4) for k, v in timings.items()}, "rows": rows,
                  "note": "Phase 2 gold encodes 'since X' as a start window; rules:v2 maps 'since' to a latest start only."}
        return result
    finally:
        driver.databases.get(db).delete()


def _cand(memory, cid):
    s = store.get(memory, cid)
    return s.candidate


def frozen_6b(driver, label):
    """D3: the frozen 6B scorer (in memory, unchanged), then the same candidate sets submitted to the store."""
    data = e6b.load()
    t0 = time.perf_counter()
    outputs = e6b.run(RulesV2(), data)
    extract_seconds = time.perf_counter() - t0
    scored = e6b.score(data, outputs)
    db, clock = common.database_name("d3"), common.Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    timings, expected_states = {}, []
    try:
        authors = sorted({p["author"] for p in data["passages"] if p.get("author")})
        if authors:
            memory.ingest(Batch(referents=tuple(Referent(a, "person", a) for a in authors)))
        clock.now = common.utc(data["observed_at"]) + timedelta(hours=1)
        source = Source("src:eval", "evaluation")
        all_ids = []
        for p, obs in e6b.observations(data):
            memory.ingest(Batch(sources=(source,), observations=(obs,)))
            cset = outputs[p["id"]]
            if cset.candidates:
                t1 = time.perf_counter()
                store.submit(memory, obs, cset)
                timings["submit"] = timings.get("submit", 0.0) + time.perf_counter() - t1
            got = [e6b._got(c) for c in cset.candidates]
            all_ids += [c.id for c in cset.candidates]
            free = list(range(len(got)))
            for e in p["expect"]:
                w = e6b._expected(e)
                j = next((j for j in free if e6b._key(got[j]) == e6b._key(w)), None)
                if j is None:
                    expected_states.append({"passage": p["id"], "state": "absent"})
                    continue
                free.remove(j)
                state = pipeline.stored_state(memory, cset.candidates[j].id)
                formed = state.get("status") == "formed" and pipeline.believed(memory, state.get("claim"), clock.now)
                expected_states.append({"passage": p["id"], "modality": w["modality"], "commitment": w["commitment"],
                                        "attribution": w["attribution"], "relations": w["relations"],
                                        "status": state.get("status"),
                                        "state": "accepted_claim" if formed else "candidate_only",
                                        "reason": state["decisions"][-1][2] if state.get("decisions") else None})
        rep = {s: sum(1 for x in expected_states if x["state"] == s) for s in ("accepted_claim", "candidate_only", "absent")}
        return {"meta": common.meta(label, "D3 frozen 6B set"), "frozen_scorer": {k: v for k, v in scored.items() if k != "rows"},
                "frozen_scorer_rows": scored["rows"], "extract_seconds": round(extract_seconds, 4),
                "policy_outcomes": pipeline.first_decisions(memory, all_ids),
                "representation": rep, "expected_states": expected_states,
                "database": {**common.counts(memory), "bytes": common.size(memory)},
                "timings": {k: round(v, 4) for k, v in timings.items()}}
    finally:
        driver.databases.get(db).delete()
