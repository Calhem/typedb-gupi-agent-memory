"""The frozen Phase 7A diagnostic sample (docs/evaluation/phase-7a/SAMPLING.md).

    uv run python -I -m gupi.benchmarks.diagnosis.sample [--write]

Deterministic and independent of any extractor output: turns are drawn from the development splits only
(LoCoMo conv-26 and conv-30; LongMemEval questions with sha256(id) mod 10 == 0), stratified, and ordered
by sha256(SEED | dataset | turn key). Only ids, strata, lengths and text hashes are written, never text.
Without --write it checks the committed sample is reproduced exactly.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import timedelta

from gupi.benchmarks import locomo, longmemeval
from gupi.benchmarks.common import ROOT

SEED = "phase7a-sample-v1"
OUT = ROOT / "docs" / "evaluation" / "phase-7a" / "sample.json"
# Fixed before any extractor output was looked at. Matching selects the targeted sample only.
WORK = re.compile(r"\b(?:job|jobs|work|works|worked|working|boss|manager|managers|company|companies|hired|quit|"
                  r"promoted|promotion|colleague|colleagues|coworker|coworkers|co-worker|office|career|employer|"
                  r"intern|internship|joined|left|resigned|reports? to|team lead|startup|position|role)\b", re.I)


def _rank(dataset, key):
    return hashlib.sha256(f"{SEED}|{dataset}|{key}".encode()).hexdigest()


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def locomo_turns():
    """Every development turn exactly as the adapter turns it into an observation (same keys and text)."""
    out = []
    for s in locomo.load("dev"):
        sid = s["sample_id"]
        conv = s["conversation"]
        for i, when, turns in locomo.sessions(s):
            for j, t in enumerate(turns):
                text = locomo.turn_text(t)
                out.append({"key": f"{sid}:{t['dia_id']}", "conversation": sid, "session": i, "position": j,
                            "speaker_is": "a" if t["speaker"] == conv["speaker_a"] else "b",
                            "at": (when + timedelta(seconds=j)).isoformat(), "chars": len(text),
                            "has_caption": bool(t.get("blip_caption")), "text_sha256": _sha(text), "_text": text})
    return out


def longmemeval_turns():
    """Every distinct development turn as the adapter creates it (one per session version)."""
    versions = {}
    for q in longmemeval.load("dev"):
        for sid, date, turns in zip(q["haystack_session_ids"], q["haystack_dates"], q["haystack_sessions"]):
            versions.setdefault(longmemeval.context_id(sid, date, turns), (sid, date, turns))
    out = []
    for cid, (sid, date, turns) in sorted(versions.items()):
        for i, t in enumerate(turns):
            out.append({"key": f"{cid}:{i}", "conversation": cid, "session": sid, "position": i, "speaker_is": t["role"],
                        "at": (longmemeval.parse_date(date) + timedelta(seconds=i)).isoformat(), "chars": len(t["content"]),
                        "has_answer": bool(t.get("has_answer")), "text_sha256": _sha(t["content"]), "_text": t["content"]})
    return out


def _terciles(turns):
    lengths = sorted(t["chars"] for t in turns)
    cuts = (lengths[len(lengths) // 3], lengths[2 * len(lengths) // 3])
    return cuts, (lambda n: "short" if n < cuts[0] else "medium" if n < cuts[1] else "long")


def draw(dataset, turns, group_of, per_cell):
    """Representative: per (group, length tercile) cell, the per_cell lowest-ranked turns."""
    cuts, tercile = _terciles(turns)
    cells = {}
    for t in turns:
        cells.setdefault((group_of(t), tercile(t["chars"])), []).append(t)
    chosen = []
    for cell in sorted(cells):
        ranked = sorted(cells[cell], key=lambda t: _rank(dataset, t["key"]))
        chosen += [{**t, "stratum": f"{cell[0]}/{cell[1]}"} for t in ranked[:per_cell]]
    return cuts, chosen


def targeted(dataset, turns, exclude, n):
    """Diagnostic: the n lowest-ranked turns matching WORK, not already in the representative sample."""
    pool = [t for t in turns if WORK.search(t["_text"]) and t["key"] not in exclude]
    return len(pool), [{**t, "stratum": "targeted/work-vocabulary"} for t in sorted(pool, key=lambda t: _rank(dataset, t["key"]))[:n]]


def build():
    out = {"seed": SEED, "protocol": "docs/evaluation/phase-7a/SAMPLING.md", "datasets": {}}
    for dataset, turns, group_of, per_cell in (
            ("locomo", locomo_turns(), lambda t: t["conversation"], 5),          # 2 conversations x 3 terciles x 5
            ("longmemeval", longmemeval_turns(), lambda t: t["speaker_is"], 5)):  # 2 roles x 3 terciles x 5
        cuts, rep = draw(dataset, turns, group_of, per_cell)
        pool, tgt = targeted(dataset, turns, {t["key"] for t in rep}, 20)
        strip = lambda ts: [{k: v for k, v in t.items() if not k.startswith("_")} for t in ts]  # noqa: E731
        out["datasets"][dataset] = {"eligible_turns": len(turns), "length_tercile_cuts_chars": list(cuts),
                                    "representative": strip(rep), "targeted_pool": pool, "targeted": strip(tgt)}
    return out


def texts():
    """{(dataset, key): text} for the sampled turns: used only in memory, never written."""
    s = json.loads(OUT.read_text())
    want = {(d, t["key"]): t["text_sha256"] for d, v in s["datasets"].items() for part in ("representative", "targeted")
            for t in v[part]}
    found = {}
    for dataset, turns in (("locomo", locomo_turns()), ("longmemeval", longmemeval_turns())):
        for t in turns:
            if (dataset, t["key"]) in want:
                if _sha(t["_text"]) != want[(dataset, t["key"])]:
                    raise ValueError(f"{dataset} {t['key']}: text differs from the frozen sample")
                found[(dataset, t["key"])] = t["_text"]
    return found


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--write", action="store_true")
    args = p.parse_args(argv)
    s = build()
    if args.write:
        if OUT.exists():
            print(f"{OUT} exists: the sample is frozen", file=sys.stderr)
            return 1
        OUT.write_text(json.dumps(s, indent=1) + "\n")
        print(f"wrote {OUT}")
        return 0
    same = json.loads(OUT.read_text()) == json.loads(json.dumps(s))
    print(json.dumps({"reproduces_frozen_sample": same}))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
