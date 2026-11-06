"""Phase 8G: does the 8F result replicate on the second development conversation? (docs/evaluation/phase-8g/protocol.md)

    uv run python -I -m gupi.benchmarks.phase8g_replication cases --conversation ID --ledgers NAME=FILE ... --out FILE --key FILE
    uv run python -I -m gupi.benchmarks.phase8g_replication temporal --conversation ID --ledgers NAME=FILE ... --judges FILE FILE --key FILE --json PATH
    uv run python -I -m gupi.benchmarks.phase8g_replication verdict --agreement PATH

The 8F scorer is reused unchanged and is only ever called. This adds what 8F did not measure: whether the classifier's agreement
is correct or merely mechanical. Two blind judges decide each activity's state from the conversation, without seeing who proposed
the activity or what state anyone gave it. Their agreement is the only reference used, it is Claude's, and it is not gold.
Cases quote the conversation, so cases, keys and judgements stay private. Only counts leave this module.
"""

import argparse
import json
import random
from collections import Counter
from datetime import timedelta
from itertools import combinations
from pathlib import Path

from gupi.benchmarks import phase8e_activity as e
from gupi.benchmarks import phase8f_agreement as f

JUDGED = ("engaged", "ended", "unknown", "contradictory", "not_one_activity")
SAME_MEANING = {"confirmed": "engaged", "presumed": "unknown", "contested": "contradictory"}   # the manual: engaged needs direct evidence


def mapped(state):
    return SAME_MEANING.get(state, state)


def computed(ledger, said_at, speakers, at):
    """{activity id: (state in the manual's words, the turns that decided it)}, from the unchanged classifier."""
    out = {}
    for a in f.as_activities(ledger, said_at, speakers):
        state, basis = e.status(a, at)
        out[a.id] = ("contradictory", tuple(m.key for m in a.used())) if e.unreconciled(a) else (mapped(state), tuple(_turn(b) for b in basis))
    return out


def _turn(claim_id):
    return ":".join(claim_id.split(":")[:2])


def build_cases(ledgers, seed=8):
    """Every activity from every ledger as an anonymous case: person and quotes only, in random order. No label, role or state."""
    rows = [(name, a) for name, l in ledgers.items() for a in l.get("activities", ())]
    random.Random(seed).shuffle(rows)
    cases, key = [], {}
    for i, (name, a) in enumerate(rows, 1):
        case = f"c{i:03d}"
        key[case] = [name, a["id"]]
        cases.append({"case": case, "person": a["person"], "evidence": [{"turn": m["turn"], "quote": m["quote"]} for m in a.get("mentions", ())]})
    return cases, key


def judged(judgement):
    return {j["case"]: j["state"] for j in judgement.get("judgements", ()) if j.get("state") in JUDGED}


def reference(first, second, key):
    """{(ledger, activity): state} where both judges agree. Anything else is undecided, and is never settled here."""
    a, b = judged(first), judged(second)
    return {tuple(key[c]): a[c] for c in key if c in a and c in b and a[c] == b[c]}


def accuracy(ledger, name, ref, states, end_states):
    """One ledger's written state, and each computed state, against the judges. `unsafe` claims more than the reference;
    `missed` claims less. Activities the judges did not agree on, or found to be not one activity, are left out."""
    def score(state_of):
        rows = [(state_of(i), s) for i, s in here.items()]
        return {"n": len(rows), "correct": sum(x == y for x, y in rows),
                "unsafe": sum(x in ("engaged", "ended") and y == "unknown" for x, y in rows),
                "wrong_way": sum({x, y} == {"engaged", "ended"} for x, y in rows),
                "missed": sum(x == "unknown" and y in ("engaged", "ended") for x, y in rows)}
    written = {a["id"]: a.get("final_state") for a in ledger.get("activities", ())}
    here = {i: s for (n, i), s in ref.items() if n == name and s != "not_one_activity" and i in states}
    return {"written": score(written.get), "computed": score(lambda i: states[i][0]), "computed_at_end": score(lambda i: end_states[i][0]),
            "not_one_activity": sum(1 for (n, _), s in ref.items() if n == name and s == "not_one_activity"),
            "decided": sum(1 for (n, _) in ref if n == name), "activities": len(written)}


def decompose(x, y, names, ref, sx, sy, texts, speakers):
    """Where the classifier's agreement comes from, across activities two ledgers both have. A gain is correct and evidence-based
    only if the same state rests on the same turns; `by_default` is two unknowns with nothing deciding either."""
    ux, uy = f.units(x, texts, speakers), f.units(y, texts, speakers)
    aligned, _ = f.align(ux, uy, f.match(ux, uy), 0.5)
    wx, wy = ({a["id"]: a.get("final_state") for a in l.get("activities", ())} for l in (x, y))
    out = Counter()
    for i, j in aligned:
        (cx, ex), (cy, ey) = sx[i], sy[j]
        kind = {(True, True): "both_agree", (False, True): "gained", (True, False): "lost", (False, False): "neither"}[(wx[i] == wy[j], cx == cy)]
        out[kind] += 1
        if kind == "gained":
            rx, ry = ref.get((names[0], i)), ref.get((names[1], j))
            if rx is None or ry is None or rx == "not_one_activity" or ry == "not_one_activity":
                out["gained_undecided"] += 1
            elif rx != cx or ry != cy:
                out["gained_incorrect"] += 1
            elif not ex and not ey:
                out["gained_correct_by_default"] += 1
            elif set(ex) & set(ey):
                out["gained_correct_same_evidence"] += 1
            else:
                out["gained_correct_different_evidence"] += 1
    return {"aligned": len(aligned), **{k: out[k] for k in sorted(out)}}


def burden(ledger, turns):
    """What a reviewer must look at when nothing is accepted automatically."""
    n = {k: len(ledger.get(k, ())) for k in ("activities", "not_same", "contradictions", "review")}
    items = sum(n.values())
    return {**n, "items": items, "per_100_turns": round(100 * items / turns, 1),
            "inferred": sum(a.get("basis") == "inferred" for a in ledger.get("activities", ()))}


def contradiction_clusters(ledgers):
    """Reported contradictions grouped by shared turns across ledgers: how many did more than one ledger report?"""
    rows = [(n, frozenset(c.get("turns", ()))) for n, l in ledgers.items() for c in l.get("contradictions", ())]
    parent = list(range(len(rows)))

    def root(i):
        while parent[i] != i:
            i = parent[i]
        return i
    for i, j in combinations(range(len(rows)), 2):
        if rows[i][1] & rows[j][1]:
            parent[root(i)] = root(j)
    groups = {}
    for i, (n, _) in enumerate(rows):
        groups.setdefault(root(i), set()).add(n)
    sizes = Counter(len(v) for v in groups.values())
    return {"reports": len(rows), "distinct": len(groups), "by_number_of_ledgers": {str(k): sizes[k] for k in sorted(sizes)}}


def correction(pair):
    return f.correction_share(pair)


def verdict(agreement, thresholds):
    """The frozen 8F criteria, computed from a scorer output and nothing else. Reader names A, B, C1 and C2 as in 8F."""
    t, p = thresholds, agreement["pairs"]
    ab = p["A|B"]
    c1 = {"mention_f1": ab["mention_f1"] >= t["mention_f1"], "activity_f1": ab["activity_f1"] >= t["activity_f1"],
          "adjusted_rand": ab["adjusted_rand"] >= t["adjusted_rand"], "bcubed_f1": ab["bcubed"][2] >= t["bcubed_f1"]}
    c2 = {"merge_rate": ab["merge_rate"] <= t["max_merge_rate"],
          "invented_continuity": all(v <= t["max_invented_continuity"] for v in agreement["invented_continuity"].values())}
    c3 = {"valid_evidence": all(v["valid_share"] >= t["min_valid_evidence"] for v in agreement["evidence"].values())}
    shared = ab["contradictions_shared"] >= 1
    each = all(p[f"A|{c}"]["contradictions_shared"] >= 1 or p[f"B|{c}"]["contradictions_shared"] >= 1 for c in ("C1", "C2"))
    c4 = {"final_state_kappa": (ab["final_state_kappa"] or 0) >= t["final_state_kappa"], "shared_conflict": shared and each}
    good = [c for c in ("C1", "C2") if all(p[f"{r}|{c}"]["mention_f1"] >= t["mention_f1"] and p[f"{r}|{c}"]["adjusted_rand"] >= t["adjusted_rand"] for r in "AB")]
    c5 = {"automated_reaches_readers": bool(good),
          "correction_share": any(all(correction(p[f"{r}|{c}"]) <= t["max_correction_share"] for r in "AB") for c in good)}
    criteria = {"1_reproducible": c1, "2_merges_continuity": c2, "3_provenance": c3, "4_temporal_ambiguity": c4, "5_automation": c5}
    return {"criteria": criteria, "passed": {k: all(v.values()) for k, v in criteria.items()},
            "automated_reaching_readers": good, "correction_share": {f"{r}|{c}": correction(p[f"{r}|{c}"]) for c in ("C1", "C2") for r in "AB"}}


def load_ledgers(items):
    return {n: json.loads(Path(p).read_text(encoding="utf-8")) for n, p in (x.split("=", 1) for x in items)}


def temporal(ledgers, first, second, key, conversation):
    from gupi.benchmarks import phase8c
    texts, speakers = f.load_texts(conversation)
    requests = phase8c.requests(phase8c.samples([conversation])[0])
    said_at = {o.record_key.split(":", 1)[1]: o.observed_at for o, _, _ in requests}
    last = max(said_at.values())
    after, at_end = {}, {}
    for n, l in ledgers.items():
        after[n] = computed(l, said_at, speakers, last + timedelta(days=1))       # as 8F asked it
        at_end[n] = computed(l, said_at, speakers, last)                          # at the end, as the manual asks
    ref = reference(first, second, key)
    a, b = judged(first), judged(second)
    both = sorted(set(a) & set(b))
    pairs = {f"{x}|{y}": decompose(ledgers[x], ledgers[y], (x, y), ref, after[x], after[y], texts, speakers) for x, y in combinations(ledgers, 2)}
    return {"note": "Reference is agreement between two blind Claude judges. Not gold, and not a human reading.",
            "judges": {"cases": len(key), "both_answered": len(both), "agree": sum(a[c] == b[c] for c in both),
                       "kappa": f.kappa([a[c] for c in both], [b[c] for c in both]), "reference_states": dict(Counter(ref.values()))},
            "accuracy": {n: accuracy(l, n, ref, after[n], at_end[n]) for n, l in ledgers.items()},
            "computed_states": {n: dict(Counter(s for s, _ in after[n].values())) for n in ledgers},
            "written_states": {n: dict(Counter(x.get("final_state") for x in l.get("activities", ()))) for n, l in ledgers.items()},
            "pairs": pairs, "burden": {n: burden(l, len(texts)) for n, l in ledgers.items()}, "contradictions": contradiction_clusters(ledgers)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=("cases", "temporal", "verdict"))
    p.add_argument("--conversation")
    p.add_argument("--ledgers", nargs="+")
    p.add_argument("--judges", nargs=2)
    p.add_argument("--agreement")
    p.add_argument("--out")
    p.add_argument("--key")
    p.add_argument("--json")
    args = p.parse_args(argv)
    if args.command == "verdict":
        thresholds = json.loads(Path("benchmarks/phase8f.json").read_text())["thresholds"]
        out = verdict(json.loads(Path(args.agreement).read_text()), thresholds)
    elif args.command == "cases":
        cases, key = build_cases(load_ledgers(args.ledgers))
        Path(args.out).write_text(json.dumps(cases, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        Path(args.key).write_text(json.dumps(key) + "\n")
        print(len(cases), "cases")
        return 0
    else:
        first, second = (json.loads(Path(x).read_text(encoding="utf-8")) for x in args.judges)
        out = temporal(load_ledgers(args.ledgers), first, second, json.loads(Path(args.key).read_text()), args.conversation)
    print(json.dumps(out, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
