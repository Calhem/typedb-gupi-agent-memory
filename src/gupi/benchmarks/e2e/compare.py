"""Compare two Phase 6D runs, ignoring what is expected to vary (timings, sizes, database names, dates).

    uv run python -I -m gupi.benchmarks.e2e.compare feasibility feasibility-repeat
"""

import json
import sys

from gupi.benchmarks.e2e import manifest

OUT = manifest.OUT.parent

VARIES = ("seconds", "latency", "timings", "meta", "bytes", "database", "started", "wall_seconds",
          "extract_seconds", "turns_per_second", "peak_python_rss_bytes", "total_seconds")


def _strip(x):
    if isinstance(x, dict):
        return {k: _strip(v) for k, v in x.items() if not any(k == v_ or k.endswith("_" + v_) for v_ in VARIES)}
    if isinstance(x, list):
        return [_strip(v) for v in x]
    return x


def diff(a, b, path=""):
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        out = [f"{path}.{k}" for k in sorted(set(a) ^ set(b))]
        for k in sorted(set(a) & set(b)):
            out += diff(a[k], b[k], f"{path}.{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}[len]"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, f"{path}[{i}]")]
    return [] if a == b else [path]


def main(argv=None):
    a, b = (argv or sys.argv[1:])[:2]
    report = {}
    for path in sorted((OUT / a).glob("*.json")):
        other = OUT / b / path.name
        if not other.exists():
            report[path.stem] = "missing in " + b
            continue
        d = diff(_strip(json.loads(path.read_text())), _strip(json.loads(other.read_text())))
        report[path.stem] = {"identical": not d, "differences": d[:20]}
    print(json.dumps(report, indent=1))
    return 0 if report and all(isinstance(v, dict) and v["identical"] for v in report.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
