"""Run the Phase 6D end-to-end evaluation (docs/evaluation/phase-6d/PLAN.md).

    uv run python -I -m gupi.benchmarks.e2e --label feasibility --parts world adversarial locomo-dev-slice
    uv run python -I -m gupi.benchmarks.e2e --label first-run --parts all

Writes docs/evaluation/phase-6d/<label>/<part>.json. Refuses to overwrite an existing result (a first run is
kept unchanged; later runs need a new label) and to run if the frozen manifest no longer matches. Needs
TypeDB; local only (no paid API, no LLM judge). Set GUPI_DOCKER for database sizes.
"""

import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

from gupi.benchmarks.common import ROOT
from gupi.benchmarks.e2e import adversarial, common, conversational, formation_layer, manifest, scale, world
from gupi.typedb.connection import connect

OUT = manifest.OUT.parent
PARTS = ("world", "phase2", "frozen-6b", "adversarial", "locomo-dev-slice", "locomo-heldout",
         "longmemeval-extraction", "longmemeval-subset", "scale")
SYSTEMS = ["keyword", "embedding", "structured", "hybrid", "hybrid-unfiltered"]


def _embedder():
    from gupi.benchmarks.common import CONFIG
    from gupi.embedding import FastEmbedder
    return FastEmbedder(CONFIG["embedding"]["model"])


def run_part(part, label, driver):
    if part == "world":
        return world.run(driver, label, embedder=_embedder())
    if part == "phase2":
        return formation_layer.phase2(driver, label)
    if part == "frozen-6b":
        return formation_layer.frozen_6b(driver, label)
    if part == "adversarial":
        return adversarial.run(driver, label)
    if part == "locomo-dev-slice":
        return conversational.run_locomo(driver, label, "dev", SYSTEMS, _embedder(), limit=20)
    if part == "locomo-heldout":
        return conversational.run_locomo(driver, label, "heldout", SYSTEMS, _embedder())
    if part == "longmemeval-extraction":
        return conversational.longmemeval_extraction_only(label)
    if part == "longmemeval-subset":
        return conversational.run_longmemeval_subset(driver, label)
    if part == "scale":
        return scale.run(driver, label)
    raise ValueError(part)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--label", required=True, help="run label, e.g. feasibility, first-run, repeat-1")
    p.add_argument("--parts", nargs="+", default=["all"], choices=("all",) + PARTS)
    p.add_argument("--manifest", default=str(manifest.OUT),
                   help="the frozen manifest this run must match (default: the original, version 1)")
    args = p.parse_args(argv)
    if manifest.main(["--path", args.manifest]) != 0:
        print("the frozen manifest does not match the current tree: refusing to run", file=sys.stderr)
        return 1
    used = {"path": args.manifest.replace(str(ROOT) + "/", ""),
            "sha256": hashlib.sha256(Path(args.manifest).read_bytes()).hexdigest()}
    # "all" is every part of the full run; the LoCoMo development slice belongs to the feasibility run only
    parts = tuple(x for x in PARTS if x != "locomo-dev-slice") if "all" in args.parts else args.parts
    out = OUT / args.label
    out.mkdir(parents=True, exist_ok=True)
    driver = connect()
    for part in parts:
        path = out / f"{part}.json"
        if path.exists():
            print(f"{path} exists: results are never overwritten; use a new --label", file=sys.stderr)
            return 1
        t0 = time.perf_counter()
        try:
            result = run_part(part, args.label, driver)
        except Exception as e:  # a failed part is recorded, not hidden
            result = {"meta": common.meta(args.label, part), "failed": f"{type(e).__name__}: {e}",
                      "traceback": traceback.format_exc()}
        result.setdefault("meta", {})["wall_seconds"] = round(time.perf_counter() - t0, 2)
        result["meta"]["manifest"] = used
        text = json.dumps(result, indent=1, default=str) + "\n"
        path.write_text(text.replace(str(ROOT), "<repo>").replace(str(Path.home()), "~"))  # public repo: no local paths
        print(f"{part}: {'FAILED ' + result['failed'] if 'failed' in result else 'done'} in {result['meta']['wall_seconds']}s -> {path}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
