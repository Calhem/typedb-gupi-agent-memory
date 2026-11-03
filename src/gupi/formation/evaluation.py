"""Scoring candidate extraction against the frozen Phase 6B set (tests/fixtures/formation/eval-v1.json).

    uv run python -I -m gupi.formation.evaluation [--json PATH]

**Matching.** A candidate matches an expected one when the claim type, every role's participant (by surface
text, case-insensitive) and the polarity agree. Matching is one-to-one and greedy, in order.

**Measures:**
- precision: matched / extracted
- recall: matched / expected
- the other fields (time kinds and phrases, modality, commitment, attribution, relations), scored only on
  matched pairs and reported separately

A passage with nothing to extract, for which nothing is extracted, is a correct rejection. It is counted
apart, never as an extracted claim. Offline, with no TypeDB.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from gupi.records import Observation

DATA = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "formation" / "eval-v1.json"
FIELDS = ("times", "modality", "commitment", "attribution", "asserted_by", "relations")


def load(path=DATA):
    return json.loads(Path(path).read_text())


def observations(data):
    when = datetime.fromisoformat(data["observed_at"].replace("Z", "+00:00"))
    for p in data["passages"]:
        yield p, Observation("src:eval", p["id"], p["text"], when, author_id=p.get("author"))


def run(extractor, data):
    """{passage id: CandidateSet}. Passages in one thread are read in order; earlier sets are `prior`."""
    out, threads = {}, {}
    for p, obs in observations(data):
        prior = threads.setdefault(p.get("thread"), []) if p.get("thread") else []
        cset, _ = extractor.extract(obs, prior=tuple(prior))
        out[p["id"]] = cset
        if p.get("thread"):
            prior.append(cset)
    return out


def _expected(e):
    a = e.get("attribution") or {}
    return {"type": e["type"], "roles": {r: s.casefold() for r, s in e["roles"].items()},
            "polarity": e.get("polarity", "positive"), "modality": e.get("modality", "actual"),
            "commitment": e.get("commitment", "certain"), "attribution": a.get("mode", "direct"),
            "asserted_by": (a.get("asserted_by") or "").casefold() or None,
            "times": sorted((k, ph.casefold()) for k, ph in e.get("times", ())),
            "relations": sorted(e.get("relations", ()))}


def _got(c):
    return {"type": c.claim_type, "roles": {p.role: p.surface.casefold() for p in c.participants},
            "polarity": c.polarity, "modality": c.modality, "commitment": c.commitment,
            "attribution": c.attribution.mode, "asserted_by": (c.attribution.asserted_by or "").casefold() or None,
            "times": sorted((t.kind, t.phrase.casefold()) for t in c.times),
            "relations": sorted(r.kind for r in c.relations)}


def _key(x):
    return x["type"], tuple(sorted(x["roles"].items())), x["polarity"]


def _times_agree(want, got):
    if [k for k, _ in want] != [k for k, _ in got]:
        return False
    return all(w in g or g in w for (_, w), (_, g) in zip(want, got))


def score(data, outputs):
    rows, matched, extracted, expected, correct_rejections = [], 0, 0, 0, 0
    fields = {f: [0, 0] for f in FIELDS}
    for p in data["passages"]:
        want = [_expected(e) for e in p["expect"]]
        got = [_got(c) for c in outputs[p["id"]].candidates]
        expected += len(want)
        extracted += len(got)
        if not want and not got:
            correct_rejections += 1
        free = list(range(len(got)))
        pairs, misses = [], []
        for w in want:
            j = next((j for j in free if _key(got[j]) == _key(w)), None)
            if j is None:
                misses.append(w)
                continue
            free.remove(j)
            pairs.append((w, got[j]))
        matched += len(pairs)
        for w, g in pairs:
            for f in FIELDS:
                ok = _times_agree(w["times"], g["times"]) if f == "times" else w[f] == g[f]
                fields[f][0] += ok
                fields[f][1] += 1
        rows.append({"id": p["id"], "expected": len(want), "extracted": len(got), "matched": len(pairs),
                     "false_positives": [_brief(got[j]) for j in free], "misses": [_brief(w) for w in misses],
                     "field_errors": [{"field": f, "expected": w[f], "got": g[f]} for w, g in pairs for f in FIELDS
                                      if not (_times_agree(w["times"], g["times"]) if f == "times" else w[f] == g[f])]})
    return {"passages": len(data["passages"]), "expected": expected, "extracted": extracted, "matched": matched,
            "precision": round(matched / extracted, 3) if extracted else None,
            "recall": round(matched / expected, 3) if expected else None,
            "correct_rejections": correct_rejections,
            "empty_passages": sum(1 for p in data["passages"] if not p["expect"]),
            "fields": {f: {"correct": c, "of": n} for f, (c, n) in fields.items()},
            "rows": rows}


def _brief(x):
    return f"{x['type']}({', '.join(f'{r}={s}' for r, s in sorted(x['roles'].items()))}){' NOT' if x['polarity'] == 'negative' else ''}"


def main(argv=None):
    from gupi.formation.rules_v2 import RulesV2
    parser = argparse.ArgumentParser(description="Score rules:v2 candidate extraction on the frozen 6B set.")
    parser.add_argument("--json", help="write the full results to this file")
    args = parser.parse_args(argv)
    data = load()
    result = score(data, run(RulesV2(), data))
    print(f"precision {result['matched']}/{result['extracted']} = {result['precision']}  "
          f"recall {result['matched']}/{result['expected']} = {result['recall']}  "
          f"correct rejections {result['correct_rejections']}/{result['empty_passages']}")
    for f, v in result["fields"].items():
        print(f"  {f:12} {v['correct']}/{v['of']} of matched")
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
