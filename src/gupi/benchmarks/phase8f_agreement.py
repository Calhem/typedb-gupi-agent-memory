"""Phase 8F: do different readers build the same activity ledger? (docs/evaluation/phase-8f/protocol.md)

    uv run python -I -m gupi.benchmarks.phase8f_agreement check --ledger FILE
    uv run python -I -m gupi.benchmarks.phase8f_agreement compare --ledgers A=FILE B=FILE ... --json PATH

Readers name and bound activities differently, so ids mean nothing here. Mentions are matched by overlapping quotes in the
same turn; activity grouping is then compared over matched mentions only, with measures that need no shared labels. Agreement is
not truth: where readers differ, nothing here says who is right, and with no human reference no result is called accuracy.
Only numbers and opaque ids leave this module. Ledgers quote the conversation and stay outside the repository.
"""

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import comb
from pathlib import Path

ROLES = ("start", "resume", "end", "past", "engagement", "negated", "event", "plan", "reference")
ROLE_GROUP = {"start": "boundary", "resume": "boundary", "end": "boundary", "past": "boundary", "engagement": "engaged", "negated": "negated",
              "event": "event", "plan": "plan", "reference": "reference"}
LINKS = ("clear", "probable", "unclear")
STATES = ("engaged", "ended", "unknown", "contradictory")


@dataclass(frozen=True)
class Unit:
    activity: str
    turn: str
    quote: str
    role: str
    link: str
    time: str | None
    start: int
    end: int


def problems(ledger, texts, speakers):
    """Everything wrong with a ledger's evidence: (bad, total mentions, reasons). Nothing is repaired."""
    bad, total, reasons = 0, 0, Counter()
    for a in ledger.get("activities", ()):
        if a.get("final_state") not in STATES or a.get("basis") not in ("explicit", "inferred"):
            reasons["bad activity field"] += 1
        for m in a.get("mentions", ()):
            total += 1
            why = None
            if m.get("turn") not in texts:
                why = "no such turn"
            elif not m.get("quote") or m["quote"] not in texts[m["turn"]]:
                why = "quote not in that turn"
            elif speakers[m["turn"]] != a.get("person"):
                why = "another person's words"
            elif m.get("role") not in ROLES or m.get("link") not in LINKS:
                why = "unknown role or link"
            elif m.get("time") and m["time"] not in texts[m["turn"]]:
                why = "time words not in that turn"
            if why:
                bad += 1
                reasons[why] += 1
    return bad, total, dict(reasons)


def units(ledger, texts, speakers):
    """The valid mentions, one per activity and quote. An invalid mention is dropped here and counted by `problems`."""
    out = []
    for a in ledger.get("activities", ()):
        for m in a.get("mentions", ()):
            turn, quote = m.get("turn"), m.get("quote")
            if turn in texts and quote and quote in texts[turn] and speakers[turn] == a.get("person"):
                s = texts[turn].index(quote)
                out.append(Unit(a["id"], turn, quote, m.get("role"), m.get("link"), m.get("time"), s, s + len(quote)))
    return out


def match(a, b):
    """One-to-one pairs of mentions: same turn, overlapping quotes, largest overlap first, ties by position."""
    options = []
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            if x.turn == y.turn:
                overlap = min(x.end, y.end) - max(x.start, y.start)
                if overlap > 0:
                    options.append((-overlap, i, j))
    used_a, used_b, pairs = set(), set(), []
    for _, i, j in sorted(options):
        if i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
            pairs.append((a[i], b[j]))
    return pairs


def f1(p, r):
    return round(2 * p * r / (p + r), 4) if p + r else 0.0


def adjusted_rand(left, right):
    """Chance-corrected agreement on which items are grouped together, with no shared labels."""
    n = len(left)
    if n < 2:
        return None
    cells = Counter(zip(left, right))
    index = sum(comb(v, 2) for v in cells.values())
    a = sum(comb(v, 2) for v in Counter(left).values())
    b = sum(comb(v, 2) for v in Counter(right).values())
    expected = a * b / comb(n, 2)
    top = (a + b) / 2
    return round((index - expected) / (top - expected), 4) if top != expected else 1.0


def bcubed(left, right):
    """Per-item precision and recall of grouping: how much of each item's group the other reader also grouped with it."""
    n = len(left)
    if not n:
        return 0.0, 0.0, 0.0
    p = r = 0.0
    for i in range(n):
        same_l = {j for j in range(n) if left[j] == left[i]}
        same_r = {j for j in range(n) if right[j] == right[i]}
        p += len(same_l & same_r) / len(same_r)
        r += len(same_l & same_r) / len(same_l)
    p, r = p / n, r / n
    return round(p, 4), round(r, 4), f1(p, r)


def kappa(x, y):
    """Cohen's kappa: agreement beyond chance. None when there is nothing to compare or only one category."""
    n = len(x)
    if not n:
        return None
    seen = sum(a == b for a, b in zip(x, y)) / n
    left, right = Counter(x), Counter(y)
    chance = sum(left[k] * right[k] for k in left) / n ** 2
    return round((seen - chance) / (1 - chance), 4) if chance != 1 else None


def align(a_units, b_units, pairs, threshold):
    """One-to-one activities by shared matched mentions (Dice), best first. Returns aligned pairs and the raw overlaps."""
    size_a, size_b = Counter(u.activity for u in a_units), Counter(u.activity for u in b_units)
    shared = Counter((x.activity, y.activity) for x, y in pairs)
    scored = sorted(((2 * v / (size_a[i] + size_b[j]), i, j) for (i, j), v in shared.items()), key=lambda t: (-t[0], t[1], t[2]))
    taken_a, taken_b, out = set(), set(), []
    for score, i, j in scored:
        if score >= threshold and i not in taken_a and j not in taken_b:
            taken_a.add(i)
            taken_b.add(j)
            out.append((i, j))
    return out, shared


def spans(shared, which):
    """Activities in one ledger that take at least two mentions from each of two or more activities in the other: a merge
    as seen from that side, a split from the other. Disagreement, not error."""
    touched = {}
    for pair, count in shared.items():
        if count >= 2:
            touched.setdefault(pair[which], set()).add(pair[1 - which])
    return sorted(k for k, v in touched.items() if len(v) > 1)


def contradiction_turns(ledger):
    return [frozenset(c.get("turns", ())) for c in ledger.get("contradictions", ())]


def compare(a, b, texts, speakers, threshold=0.5):
    ua, ub = units(a, texts, speakers), units(b, texts, speakers)
    pairs = match(ua, ub)
    precision, recall = len(pairs) / len(ub) if ub else 0.0, len(pairs) / len(ua) if ua else 0.0
    left, right = [x.activity for x, _ in pairs], [y.activity for _, y in pairs]
    aligned, shared = align(ua, ub, pairs, threshold)
    na, nb = len({u.activity for u in ua}), len({u.activity for u in ub})
    state = {x["id"]: x.get("final_state") for x in a.get("activities", ())}, {x["id"]: x.get("final_state") for x in b.get("activities", ())}
    states = [(state[0][i], state[1][j]) for i, j in aligned]
    merges_b, merges_a = spans(shared, 1), spans(shared, 0)
    ca, cb = contradiction_turns(a), contradiction_turns(b)
    return {"mentions": (len(ua), len(ub)), "matched": len(pairs), "mention_f1": f1(precision, recall),
            "activities": (na, nb), "aligned": len(aligned), "activity_f1": f1(len(aligned) / nb if nb else 0, len(aligned) / na if na else 0),
            "adjusted_rand": adjusted_rand(left, right), "bcubed": bcubed(left, right),
            "role_kappa": kappa([ROLE_GROUP.get(x.role, x.role) for x, _ in pairs], [ROLE_GROUP.get(y.role, y.role) for _, y in pairs]),
            "role_exact": round(sum(x.role == y.role for x, y in pairs) / len(pairs), 4) if pairs else None,
            "link_kappa": kappa([x.link for x, _ in pairs], [y.link for _, y in pairs]),
            "final_state_kappa": kappa([s[0] for s in states], [s[1] for s in states]),
            "final_state_agree": round(sum(s[0] == s[1] for s in states) / len(states), 4) if states else None,
            "merged_by_second": len(merges_b), "merged_by_first": len(merges_a),
            "merge_rate": round((len(merges_a) + len(merges_b)) / max(1, na + nb), 4),
            "contradictions": (len(ca), len(cb)), "contradictions_shared": sum(any(x & y for y in cb) for x in ca)}


def invented_continuity(ledger, last_session):
    """Activities said to be engaged at the end whose latest mention is not in the last session: continuity from silence."""
    out = []
    for a in ledger.get("activities", ()):
        turns = [m.get("turn", "") for m in a.get("mentions", ())]
        if a.get("final_state") == "engaged" and not any(t.split(":")[0] == last_session for t in turns):
            out.append(a["id"])
    return out


def consensus(first, second, automated, texts, speakers):
    """Automated against what two readers agree on. Agreement between readers is the only reference available: it is
    not gold, and everything outside it is simply undecided."""
    ua, ub, ux = units(first, texts, speakers), units(second, texts, speakers), units(automated, texts, speakers)
    both = match(ua, ub)
    keyed = [x for x, _ in both]
    with_auto = match(keyed, ux)
    index = {id(x): y for x, y in both}
    triples = [(x, index[id(x)], z) for x, z in with_auto]
    agreed = set()
    for (p, q) in combinations(range(len(both)), 2):
        if both[p][0].activity == both[q][0].activity and both[p][1].activity == both[q][1].activity:
            agreed.add((both[p][0], both[q][0]))
    apart = {(both[p][0], both[q][0]) for p, q in combinations(range(len(both)), 2)
             if both[p][0].activity != both[q][0].activity and both[p][1].activity != both[q][1].activity}
    position = {x: z for x, _, z in triples}
    found = sum(1 for p, q in agreed if p in position and q in position and position[p].activity == position[q].activity)
    falsely = sum(1 for p, q in apart if p in position and q in position and position[p].activity == position[q].activity)
    return {"agreed_mentions": len(both), "mentions_recovered": len(triples), "mention_recall": round(len(triples) / len(both), 4) if both else None,
            "agreed_links": len(agreed), "links_recovered": found, "link_recall": round(found / len(agreed), 4) if agreed else None,
            "agreed_separations": len(apart), "separations_broken": falsely, "false_merge_rate": round(falsely / len(apart), 4) if apart else None}


def correction_share(result):
    """Share of the automated activities a person would have to change to reach the other reader's: not aligned, or merged."""
    _, nb = result["activities"]
    return round((nb - result["aligned"] + result["merged_by_second"]) / nb, 4) if nb else None


def load_texts(conversation):
    from gupi.benchmarks import phase8c
    sample = phase8c.samples([conversation])[0]
    pairs = [(o.record_key.split(":", 1)[1], o.content, author) for o, author, _ in phase8c.requests(sample)]
    return {k: t for k, t, _ in pairs}, {k: a for k, _, a in pairs}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=("check", "compare"))
    p.add_argument("--ledger")
    p.add_argument("--ledgers", nargs="+", help="NAME=FILE; the first two are the readers")
    p.add_argument("--conversation", default="conv-30")
    p.add_argument("--json")
    args = p.parse_args(argv)
    texts, speakers = load_texts(args.conversation)
    last = max((k.split(":")[0] for k in texts), key=lambda s: int(s[1:]))
    if args.command == "check":
        print(json.dumps(problems(json.loads(Path(args.ledger).read_text(encoding="utf-8")), texts, speakers)))
        return 0
    ledgers = {n: json.loads(Path(f).read_text(encoding="utf-8")) for n, f in (x.split("=", 1) for x in args.ledgers)}
    names = list(ledgers)
    out = {"note": "Agreement among Claude-produced ledgers. Not accuracy; no human reference exists.", "evidence": {},
           "pairs": {}, "invented_continuity": {}, "against_reader_agreement": {}}
    for n, l in ledgers.items():
        bad, total, reasons = problems(l, texts, speakers)
        out["evidence"][n] = {"mentions": total, "invalid": bad, "valid_share": round(1 - bad / total, 4) if total else None, "why": reasons}
        out["invented_continuity"][n] = invented_continuity(l, last)
    for x, y in combinations(names, 2):
        out["pairs"][f"{x}|{y}"] = compare(ledgers[x], ledgers[y], texts, speakers)
    for n in names[2:]:
        out["against_reader_agreement"][n] = consensus(ledgers[names[0]], ledgers[names[1]], ledgers[n], texts, speakers)
    print(json.dumps(out, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
