"""Phase 8B.2: A keyword, B keyword + conversational, C = B + claim paths, on the frozen exploratory fixture.

    uv run python -I -m gupi.benchmarks.phase8_paths --questions dev --json PATH

Claims come only through the protected pipeline (recorded responses -> model:candidate-v1.1 -> candidate store ->
formation:v1). The runner approves no review item. Rules: tests/fixtures/phase8b/SCORING.md. Not a benchmark result.
"""

import argparse
import json
import re
import statistics
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gupi import evidence, paths
from gupi.formation import store
from gupi.formation.form import live_schema
from gupi.formation.model_candidate import RESPONSE_FORMAT, ModelCandidateV1
from gupi.memory import Memory
from gupi.records import Batch, Context, Observation, Referent, Source
from gupi.temporal import Answer
from gupi.typedb.connection import connect

FIXTURE = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "phase8b"
SOURCE = Source("src:g1", "conversation", label="Phase 8B fixture")
KS = (5, 10)
SYSTEMS = ("A-keyword", "B-conversational", "C-claim-paths", "C1-one-hop", "D-name-control")
NAME = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")   # the control's only entity knowledge: capitalised words


class Clock:
    now = datetime(2017, 1, 1, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


def _assertion(a, text):
    mode, claimant, kind = a.get("attr", ["direct", None, None])
    out = {"evidence": a.get("ev", text.rstrip(".")), "relation": a["rel"],
           "participants": [{"role": r, "text": t, "kind": k, "is_pronoun_or_vague": False} for r, t, k in a["p"]],
           "times": [{"text": t, "kind": k} for t, k in a["t"]], "polarity": "positive", "modality": "actual",
           "commitment": a.get("commitment", "certain"), "basis": "explicit",
           "attribution": {"mode": mode, "claimant": claimant, "claimant_kind": kind, "via": []}}
    for src, dst in (("pred", "predicate"), ("obj_text", "object_text"), ("title", "title"), ("allegation", "allegation")):
        if src in a:
            out[dst] = a[src]
    if "corr" in a:
        out["correction"] = {"kind": a["corr"][0], "cue": a["corr"][1]}
    return out


def build(memory, clock, world):
    """Every message in time order through the protected pipeline. Returns ({key: observation id}, [(key, status)])."""
    keys, statuses, prior = {}, [], {}
    schema = live_schema(memory)
    for m in sorted(world["messages"], key=lambda x: (x["at"], x["key"])):
        at = datetime.fromisoformat(m["at"].replace("Z", "+00:00"))
        clock.now = max(clock.now + timedelta(seconds=1), at)
        author = Referent(f"a:{m['author']}", "person", m["author"])
        obs = Observation(SOURCE.id, m["key"], m["text"], at, m["context"], author.id)
        memory.ingest(Batch((SOURCE,), (obs,), (author,), contexts=(Context(m["context"], "conversation"),)))
        keys[m["key"]] = obs.id
        response = {"format": RESPONSE_FORMAT, "outcome": "assertions" if m["assertions"] else "no-relevant-assertion",
                    "assertions": [_assertion(a, m["text"]) for a in m["assertions"]], "problems": []}
        cset, _ = ModelCandidateV1().extract(obs, prior=prior.get(m["context"], ()), schema=schema, response=response)
        prior[m["context"]] = prior.get(m["context"], ()) + (cset,)
        clock.now += timedelta(seconds=1)
        if cset.candidates:
            store.submit(memory, obs, cset)
            statuses += [(m["key"], store.get(memory, c.id).status) for c in cset.candidates]
    clock.now += timedelta(days=1)
    never = set(world["identity"]["never_merge"])
    found = [s for s in memory.suggest_identities() if s.reason.startswith("same name")]
    with_names = [s for s in found if not any(n in s.reason for n in never)]
    from gupi.identity import METHOD  # the suggestions were recorded as hypotheses: a simulated reviewer accepts these
    pairs = {tuple(sorted((s.a, s.b))) for s in with_names}
    decisions = [(c.id, "accepted") for c in memory.identity_claims() if tuple(sorted(c.roles["same"])) in pairs]
    if decisions:
        memory.review_many(decisions, "simulated-reviewer", METHOD)
    clock.now += timedelta(days=1)
    return keys, statuses


def name_control(memory, q, contexts, budget, texts):
    """The control: the same budget and merge as C, but two rounds of name matching over raw text, with no claims,
    types, time or identity. If this matches C, typed claims are not what found the evidence."""
    base = paths.conversational(memory, q["text"], contexts, paths.Budget(k=50, pool=50))
    seeds = [i.observation_id for i in base.items if i.reasons[0] == "keyword"][:budget.seeds]
    names = set(NAME.findall(q["text"])) | {n for s in seeds for n in NAME.findall(texts[s])}
    linked = []
    for _ in range(2):
        hop = sorted(o for o, t in texts.items() if o not in linked and names & set(NAME.findall(t)))
        linked += hop
        names |= {n for o in hop for n in NAME.findall(texts[o])}
    order = list(base.ids[:budget.keep])
    rest = paths.interleave(linked, base.ids[budget.keep:]) + linked + base.ids
    return list(dict.fromkeys(order + rest))[:budget.k]


def ranking(memory, q, contexts, system, k, texts):
    budget = paths.Budget(k=k)
    if system == "D-name-control":
        return name_control(memory, q, contexts, budget, texts), None
    if system == "C1-one-hop":
        return paths.retrieve(memory, q["text"], contexts, paths.Budget(k=k, hops=1)).ids, None
    if system == "A-keyword":
        return evidence.keyword(memory, q["text"], contexts, k).ids, None
    if system == "B-conversational":
        return paths.conversational(memory, q["text"], contexts, budget).ids, None
    result = paths.retrieve(memory, q["text"], contexts, budget)
    return result.ids, result


def covers(path, gold_obs):
    return bool(gold_obs) and all(any(o in gold_obs for o in h.observations) for h in path.hops)


def established(path):
    return all(h.tier == "accepted" for h in path.hops) and path.overlap in (None, "confirmed")


def check(q, result, keys, memory):
    """{check: passed} for the integrity checks of SCORING.md, on system C at k = 10."""
    out, c = {}, q["checks"]
    items = {i.observation_id: i for i in result.items}
    gold = {keys[g] for g in q["gold"]}
    for name in ("overlap", "not_confirmed"):
        if name in c:
            mine = [p.overlap for p in result.paths if len(p.hops) == 2 and covers(p, gold)]
            out[name] = (all(x != "confirmed" for x in mine) if name == "not_confirmed"
                         else bool(mine) and all(x in c[name] for x in mine))
    if "structured" in c:
        s = c["structured"]
        at = datetime.fromisoformat(s["at"]).replace(tzinfo=timezone.utc)
        out["structured"] = memory.query_by_name(s["type"], s["roles"], at, semantics="v2").answer.name in s["answers"]
    if "tier" in c:
        out["tier"] = all(items[keys[k]].tier == t for k, t in c["tier"].items() if keys[k] in items) and any(
            keys[k] in items for k in c["tier"])
    if "originator" in c:
        out["originator"] = all(keys[k] in items and label in items[keys[k]].originators for k, label in c["originator"].items())
    if "pending" in c:
        out["pending"] = all(keys[k] in items and any(keys[o] in n for n in items[keys[k]].notes) for k, o in c["pending"].items())
    if "ambiguous" in c:
        out["ambiguous"] = c["ambiguous"] in result.ambiguous
    if "no_merge" in c:
        out["no_merge"] = all(p.labels.count(n) < 2 for p in result.paths for n in c["no_merge"])
    if "no_path" in c:
        out["no_path"] = not any({a, b} <= set(p.labels) for p in result.paths for a, b in c["no_path"])
    if "no_path_established" in c:
        out["no_path_established"] = not any({a, b} <= set(p.labels) and established(p)
                                             for p in result.paths for a, b in c["no_path_established"])
    return out


def severe(result):
    """SCORING.md's must-be-zero list, on what C returned."""
    bad = [f"{i.observation_id}: unresolved shown as accepted" for i in result.items
           if i.tier == "accepted" and any(n.startswith(("not accepted", "pending", paths.UNCONFIRMED)) for n in i.notes)]
    bad += [f"hop {h.claim_id} has no evidence" for p in result.paths for h in p.hops if not h.observations]
    return bad


def evaluate(memory, questions, keys, contexts, texts):
    rows = []
    for q in questions:
        gold = {keys[g] for g in q["gold"]}
        base = {}
        for system in SYSTEMS:
            t0 = time.perf_counter()
            ranked, result = ranking(memory, q, contexts, system, max(KS), texts)
            seconds = time.perf_counter() - t0
            base[system] = ranked
            row = {"question": q["id"], "class": q["cls"], "system": system, "seconds": seconds, "gold": len(gold)}
            for k in KS:
                hit = set(ranked[:k]) & gold
                row[f"recall@{k}"] = len(hit) / len(gold) if gold else None
                row[f"precision@{k}"] = len(hit) / k
                row[f"complete@{k}"] = gold <= set(ranked[:k]) if gold else None
            if result is not None:
                row["checks"] = check(q, result, keys, memory)
                row["severe"] = severe(result)
                row["truncated"] = result.truncated
                row["paths"] = len(result.paths)
                row["ids"] = ranked
                row["added@10"] = len((set(ranked) - set(base["B-conversational"])) & gold)
                row["displaced@10"] = len((set(base["B-conversational"]) - set(ranked)) & gold)
            rows.append(row)
    return rows


def summarise(rows):
    out = {}
    for system in SYSTEMS:
        sel = [r for r in rows if r["system"] == system]
        secs = sorted(r["seconds"] for r in sel)

        def mean(rs, key):
            xs = [r[key] for r in rs if r[key] is not None]
            return round(statistics.mean(xs), 4) if xs else None
        metrics = [f"{m}@{k}" for k in KS for m in ("recall", "precision", "complete")]
        out[system] = {"overall": {m: mean(sel, m) for m in metrics},
                       "by_class": {c: {"questions": sum(r["class"] == c for r in sel)} | {m: mean([r for r in sel if r["class"] == c], m) for m in metrics}
                                    for c in sorted({r["class"] for r in sel})},
                       "latency_seconds": {"p50": round(secs[len(secs) // 2], 4), "p95": round(secs[int(len(secs) * .95)], 4)}}
    c = [r for r in rows if r["system"] == "C-claim-paths"]
    checks = [(r["question"], n, v) for r in c for n, v in r["checks"].items()]
    out["integrity"] = {"checks": len(checks), "passed": sum(v for _, _, v in checks),
                        "failed": [f"{q}:{n}" for q, n, v in checks if not v],
                        "severe": [x for r in c for x in r["severe"]],
                        "added@10": sum(r["added@10"] for r in c), "displaced@10": sum(r["displaced@10"] for r in c)}
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--questions", choices=["dev", "sealed"], default="dev")
    p.add_argument("--json")
    args = p.parse_args(argv)
    world = json.loads((FIXTURE / "world.json").read_text())
    questions = json.loads((FIXTURE / f"questions-{args.questions}.json").read_text())
    driver, db, clock = connect(), f"gupi-bench-phase8b-{uuid.uuid4().hex[:8]}", Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        keys, statuses = build(memory, clock, world)
        contexts = sorted({m["context"] for m in world["messages"]})
        counts = {}
        for _, s in statuses:
            counts[s] = counts.get(s, 0) + 1
        texts = {keys[m["key"]]: m["text"] for m in world["messages"]}
        rows = evaluate(memory, questions, keys, contexts, texts)
        result = {"fixture": "exploratory, developer-authored", "questions": args.questions, "formation": counts,
                  "claims": len(memory.all_claims()), "note": "Not a benchmark or leaderboard result.",
                  "summary": summarise(rows), "rows": rows}
        s = result["summary"]
        print(json.dumps({"formation": counts, "claims": result["claims"], "integrity": s["integrity"]}, indent=0))
        for system in SYSTEMS:
            print(system, s[system]["overall"], s[system]["latency_seconds"])
            for c, v in s[system]["by_class"].items():
                print(f"   {c:11} n={v['questions']:2} R@5 {v['recall@5']} R@10 {v['recall@10']} complete@10 {v['complete@10']}")
        if args.json:
            Path(args.json).write_text(json.dumps(result, indent=1, default=str) + "\n")
    finally:
        driver.databases.get(db).delete()


if __name__ == "__main__":
    main()
