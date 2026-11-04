"""The frozen Phase 6D evaluation manifest (docs/evaluation/phase-6d/manifest.json).

    uv run python -I -m gupi.benchmarks.e2e.manifest [--write]

Records dataset files and hashes, splits, extractor, policy and baseline versions (as source hashes), the
scoring rules, and the hardware and runtime configuration. Without --write it prints the manifest and checks
it against the committed one, so a run can verify nothing it depends on has changed.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys

from gupi.benchmarks.common import CONFIG, ROOT, SPLIT

OUT = ROOT / "docs" / "evaluation" / "phase-6d" / "manifest.json"

DATASETS = {
    "D1": {"name": "Phase 4 frozen retrieval world and questions",
           "files": ["tests/fixtures/retrieval/world.json", "tests/fixtures/retrieval/questions.json"],
           "split": "all 15 questions, 11 messages", "frozen_in": "be7c01a",
           "prior_use": "implementer-written; answer semantics v1/v2 developed and reported on it; not used to write rules:v2",
           "independent": False},
    "D2": {"name": "Phase 2 held-out conversations",
           "files": ["tests/fixtures/conversations/heldout/h1-new-cfo.json",
                     "tests/fixtures/conversations/heldout/h2-product-lead.json",
                     "tests/fixtures/conversations/heldout/h3-pronouns-and-generic.json"],
           "split": "held-out (12 messages, 12 gold claims)", "frozen_in": "814f501",
           "prior_use": "written before any extractor; rules:v2 held-out recall reported once in 6B",
           "independent": True},
    "D3": {"name": "Phase 6B frozen extraction set",
           "files": ["tests/fixtures/formation/eval-v1.json"], "split": "all 32 passages", "frozen_in": "a5a1671",
           "prior_use": "implementer-written just before rules:v2 with its scope in mind; first run reported in 6B",
           "independent": False},
    "D4": {"name": "Phase 6C adversarial cases (development tests)",
           "files": ["tests/fixtures/formation/adversarial-v1.json"], "split": "all 17 cases", "frozen_in": "b510a32",
           "prior_use": "development tests written by the qualification's designer; first run 17/17 via form()",
           "independent": False},
    "D5": {"name": "LoCoMo", "files": [".data/locomo/locomo10.json"], "split": "held-out conversations (split.json)",
           "prior_use": "Phase 5 held-out retrieval first run reported; second exposure, no tuning",
           "licence": "CC BY-NC 4.0 (research use; content never committed)", "independent": True},
    "D6": {"name": "LongMemEval S cleaned", "files": [".data/longmemeval/longmemeval_s_cleaned.json"],
           "split": "held-out (447); TypeDB run on the pre-registered 64-question subset (config.json)",
           "prior_use": "Phase 5 held-out retrieval first run reported; second exposure, no tuning",
           "licence": "MIT", "independent": True},
}

CODE = {  # versions of what is evaluated, as hashes of the source that implements it
    "extractor rules:v2": "src/gupi/formation/rules_v2.py",
    "candidate IR gupi.candidate/1": "src/gupi/formation/candidate.py",
    "validation": "src/gupi/formation/validate.py",
    "policy formation:v1": "src/gupi/formation/form.py",
    "candidate store (core/0012)": "src/gupi/formation/store.py",
    "answer semantics v2": "src/gupi/answering_v2.py",
    "query": "src/gupi/query.py",
    "qualification": "src/gupi/qualification.py",
    "evidence retrievers (Phase 5)": "src/gupi/evidence.py",
    "keyword answer baseline and Phase 4 scorer": "src/gupi/retrieval_eval.py",
    "rules:v1 (Phase 4 pipeline)": "src/gupi/extraction/rules.py",
    "time expressions": "src/gupi/timeexpr.py",
    "6B scorer": "src/gupi/formation/evaluation.py",
    "6C adversarial scorer": "scripts/evaluate_adversarial.py",
    "retrieval benchmark config": "benchmarks/config.json",
    "retrieval benchmark split": "benchmarks/split.json",
}

SCORING = {
    "formation_match": "one-to-one greedy by claim type and role surfaces (case-folded); D3 also polarity (frozen 6B scorer)",
    "temporal": "stored claim start window, end window and ongoing-at-observation, each exactly equal to the gold (D1, D2)",
    "representation": "gold claim -> accepted claim in TypeDB | stored candidate only | absent",
    "retrieval": "recall@k = |gold in top k| / |gold|; precision@5 = |gold in top 5| / 5; GUPI citations: set precision/recall",
    "answers": "frozen gupi.retrieval_eval.score; missing (error or none) counted apart from incorrect",
    "unsupported_definitive": "definitive TRUE/FALSE where gold is UNKNOWN/NOT_YET_KNOWN/CONTESTED, or any deciding evidence not direct",
    "adversarial": "frozen scripts/evaluate_adversarial.score, through the candidate store",
    "llm_judge": "none",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _cmd(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=30).stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def runtime():
    from importlib.metadata import PackageNotFoundError, version

    def v(p):
        try:
            return version(p)
        except PackageNotFoundError:
            return None
    return {"python": platform.python_version(), "platform": platform.platform(terse=True),
            "machine": _cmd("sysctl", "-n", "hw.model"), "cpu": _cmd("sysctl", "-n", "machdep.cpu.brand_string"),
            "cpu_count": _cmd("sysctl", "-n", "hw.ncpu"), "memory_bytes": _cmd("sysctl", "-n", "hw.memsize"),
            "packages": {p: v(p) for p in ("typedb-driver", "fastembed", "onnxruntime", "numpy")},
            "typedb": "typedb/typedb:3.14.1 in Docker (compose.yaml), 127.0.0.1:1734",
            "embedding_model": CONFIG["embedding"]}


def build():
    data = {}
    for key, d in DATASETS.items():
        files = {}
        for f in d["files"]:
            p = ROOT / f
            files[f] = {"sha256": sha256(p), "bytes": p.stat().st_size} if p.exists() else None
        data[key] = {**d, "files": files}
    return {
        "phase": "6D", "frozen": "2026-11-04",
        "protocol": "docs/evaluation/phase-6d/PLAN.md",
        "datasets": data,
        "splits": {"locomo_heldout": SPLIT["locomo"]["heldout"], "longmemeval_heldout_count": SPLIT["longmemeval_s_cleaned"]["heldout_count"],
                   "longmemeval_typedb_subset": "benchmarks/config.json amendment 4 (embedding_subset, 64 ids)"},
        "code": {name: {"path": p, "sha256": sha256(ROOT / p)} for name, p in CODE.items()},
        "scoring": SCORING,
        "runtime": runtime(),
        "not_used": ["specialist M1 materials", "paid APIs", "LLM judges", "new downloads"],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--write", action="store_true")
    args = p.parse_args(argv)
    m = build()
    if args.write:
        OUT.write_text(json.dumps(m, indent=1, sort_keys=False) + "\n")
        print(f"wrote {OUT}")
        return 0
    frozen = json.loads(OUT.read_text())
    drift = sorted(k for k in ("datasets", "code", "scoring", "splits") if frozen.get(k) != m[k])
    print(json.dumps({"matches_frozen_manifest": not drift, "differs": drift}))
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
