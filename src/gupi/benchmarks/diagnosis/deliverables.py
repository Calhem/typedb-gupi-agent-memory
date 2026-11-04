"""Generate the Phase 7A sample-manifest.json and sample-results.csv from the committed files (no dataset
text, reproducible).

    uv run python -I -m gupi.benchmarks.diagnosis.deliverables
"""

import csv
import hashlib
import json

from gupi.benchmarks.common import ROOT
from gupi.benchmarks.diagnosis import sample

DIR = sample.OUT.parent
FIXTURES = ROOT / "tests" / "fixtures" / "diagnosis"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    s = json.loads(sample.OUT.read_text())
    six_d = json.loads((ROOT / "docs" / "evaluation" / "phase-6d" / "manifest.json").read_text())
    return {
        "phase": "7A", "frozen": "2026-11-04", "protocol": "docs/evaluation/phase-7a/SAMPLING.md",
        "sources": {"locomo": six_d["datasets"]["D5"]["files"], "longmemeval": six_d["datasets"]["D6"]["files"],
                    "versions": {"locomo": "github.com/snap-research/locomo commit cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc",
                                 "longmemeval": "huggingface.co/datasets/xiaowu0162/longmemeval-cleaned revision 98d7416c24c778c2fee6e6f3006e7a073259d48f"}},
        "splits_used": {"locomo": "development: conv-26, conv-30 (benchmarks/split.json)",
                        "longmemeval": "development: sha256(question_id) mod 10 == 0 (benchmarks/split.json)"},
        "sampling": {"seed": s["seed"], "rank": "sha256('<seed>|<dataset>|<turn key>'), lowest first",
                     "representative": "LoCoMo: conversation x length tercile x 5; LongMemEval: role x length tercile x 5",
                     "targeted": "20 per dataset matching the WORK pattern in gupi/benchmarks/diagnosis/sample.py, kept separate",
                     "counts_subset": "sha256('phase7a-counts-v1|<dataset>|<key>') mod 20 == 0 (gupi/benchmarks/diagnosis/counts.py)"},
        "files": {p.name: _sha(p) for p in (sample.OUT, DIR / "annotations.json", FIXTURES / "probes-v1.json",
                                            FIXTURES / "probes-v2.json")},
        "sample": {d: {"eligible_turns": v["eligible_turns"], "length_tercile_cuts_chars": v["length_tercile_cuts_chars"],
                       "targeted_pool": v["targeted_pool"],
                       "representative": [{k: t[k] for k in ("key", "stratum", "chars", "text_sha256")} for t in v["representative"]],
                       "targeted": [{k: t[k] for k in ("key", "stratum", "chars", "text_sha256")} for t in v["targeted"]]}
                   for d, v in s["datasets"].items()},
    }


def results_rows():
    ann = json.loads((DIR / "annotations.json").read_text())
    cls = json.loads((DIR / "classification.json").read_text())["results"]
    rows = []
    for dataset, parts in ann["datasets"].items():
        for part, turns in parts.items():
            got = {r["key"]: r for r in cls[f"{dataset}/{part}"]["rows"]}
            for t in turns:
                r = got[t["key"]]
                base = {"dataset": dataset, "sample": part, "turn_key": t["key"], "stratum": r["stratum"], "chars": r["chars"],
                        "extractor_candidates": r["extractor"]["candidates"],
                        "domain_verbs": " ".join(r["domain_verbs"]),
                        "extractor_rejected_clauses": len(r["extractor"]["rejected_clauses"])}
                if not t["facts"]:
                    rows.append({**base, "fact": 0, "category": "C", "domain": "", "about": "", "explicit": "", "needs": "",
                                 "earliest_stage": "", "label": "no relevant extractable fact"})
                for n, f in enumerate(t["facts"], 1):
                    rows.append({**base, "fact": n, "category": f["category"], "domain": f["domain"], "about": f["about"],
                                 "explicit": f["explicit"], "needs": "; ".join(f["needs"]), "earliest_stage": f["stage"],
                                 "label": f["note"]})
    return rows


def main():
    (DIR / "sample-manifest.json").write_text(json.dumps(manifest(), indent=1) + "\n")
    rows = results_rows()
    with open(DIR / "sample-results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"sample-manifest.json; sample-results.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
