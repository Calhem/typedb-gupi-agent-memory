"""Shared pieces: question records, metrics, the run loop, footprint measurement."""

import json
import os
import resource
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from gupi import evidence

ROOT = Path(__file__).resolve().parents[3]
CONFIG = json.loads((ROOT / "benchmarks" / "config.json").read_text())
SPLIT = json.loads((ROOT / "benchmarks" / "split.json").read_text())
KS = CONFIG["k"]
DEPTH = CONFIG["candidates_per_retriever"]


@dataclass
class BenchQuestion:
    id: str
    text: str
    category: str
    contexts: list                       # scope
    asked_at: object
    gold: dict                           # unit name -> set of gold unit ids ("turn" -> observation ids, ...)
    unit_of: dict = field(default_factory=dict)  # unit name -> {observation id: unit id} for non-turn units


def rank_units(ids, mapping):
    """Turn ranking -> ranking of larger units (first appearance)."""
    out, seen = [], set()
    for i in ids:
        u = mapping.get(i)
        if u is not None and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def metrics(ranked, gold):
    m = {}
    for k in KS:
        top = set(ranked[:k])
        m[f"recall@{k}"] = len(top & gold) / len(gold)
        m[f"hit@{k}"] = float(bool(top & gold))
    m["mrr"] = next((1.0 / r for r, u in enumerate(ranked, 1) if u in gold), 0.0)
    return m


def run_questions(memory, questions, systems, embedder):
    """Every system on every question. Returns per-question rows."""
    rows = []
    for q in questions:
        for system in systems:
            t0 = time.perf_counter()
            if system == "keyword":
                r = evidence.keyword(memory, q.text, q.contexts, DEPTH)
            elif system == "embedding":
                r = evidence.embedding(memory, embedder, q.text, q.contexts, DEPTH)
            elif system == "structured":
                r = evidence.structured(memory, q.text, q.contexts, q.asked_at, DEPTH)
            elif system == "hybrid-unfiltered":
                r = evidence.hybrid(memory, embedder, q.text, q.contexts, q.asked_at, DEPTH, CONFIG["hybrid"]["rrf_k"],
                                    use_structure=False)
            else:
                r = evidence.hybrid(memory, embedder, q.text, q.contexts, q.asked_at, DEPTH, CONFIG["hybrid"]["rrf_k"])
            seconds = time.perf_counter() - t0
            for unit, gold in q.gold.items():
                if not gold:
                    continue
                ranked = r.ids if unit == "turn" else rank_units(r.ids, q.unit_of[unit])
                rows.append({"question": q.id, "category": q.category, "system": system, "unit": unit,
                             "seconds": seconds, "returned": len(r.ids), **metrics(ranked, gold)})
    return rows


def summarise(rows):
    """Mean metrics per (unit, system), overall and per category, plus latency."""
    out = {}
    for unit in sorted({r["unit"] for r in rows}):
        for system in sorted({r["system"] for r in rows}):
            sel = [r for r in rows if r["unit"] == unit and r["system"] == system]
            if not sel:
                continue
            keys = [k for k in sel[0] if k.startswith(("recall@", "hit@")) or k == "mrr"]

            def mean(rs):
                return {k: round(statistics.mean(r[k] for r in rs), 4) for k in keys} | {"questions": len(rs)}
            secs = sorted(r["seconds"] for r in sel)
            out.setdefault(unit, {})[system] = {
                "overall": mean(sel),
                "by_category": {c: mean([r for r in sel if r["category"] == c]) for c in sorted({r["category"] for r in sel})},
                "empty_results": sum(1 for r in sel if r["returned"] == 0),
                "latency_seconds": {"median": round(secs[len(secs) // 2], 4), "p95": round(secs[int(len(secs) * 0.95)], 4)},
            }
    return out


def database_bytes(database):
    """Size of the database's directory inside the TypeDB container (None if it cannot be measured)."""
    docker = os.environ.get("GUPI_DOCKER") or shutil.which("docker")
    if not docker:
        return None
    try:
        out = subprocess.run([docker, "exec", "gupi-typedb", "du", "-sk",
                              f"/var/lib/typedb/data/{database}"], capture_output=True, text=True, timeout=60)
        return int(out.stdout.split()[0]) * 1024 if out.returncode == 0 else None
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def peak_rss_bytes():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss if sys.platform == "darwin" else rss * 1024  # macOS reports bytes, Linux kilobytes
