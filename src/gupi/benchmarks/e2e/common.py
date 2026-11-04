"""Shared pieces of the Phase 6D runner: clock, run metadata, gold isolation, database checks, timing."""

import copy
import statistics
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime

from typedb.driver import TransactionType

from gupi.benchmarks.common import ROOT, database_bytes, peak_rss_bytes
from gupi.extraction.contract import normalise
from gupi.typedb.connection import rows as query_rows
from gupi.typedb.connection import transaction

COUNTED = ("observation", "memory-candidate", "formation-decision", "formed-into", "claim", "review",
           "correction-suggestion", "embedding")


class Clock:
    def __init__(self, now=None):
        self.now = now or datetime(2025, 1, 1, tzinfo=UTC)

    def __call__(self):
        return self.now


def utc(text):
    text = text if "T" in text else text + "T00:00:00Z"
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def git_state():
    def git(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(git("status", "--porcelain", "--untracked-files=no"))}


def public(question):
    """What a system may see of a question: everything except its gold. Systems only ever get this."""
    q = copy.deepcopy(question)
    q.pop("gold", None)
    return q


def database_name(prefix):
    return f"gupi-6d-{prefix}-{uuid.uuid4().hex[:8]}"


def counts(memory):
    """Instance counts in the run's own database, read back from TypeDB (proves which database was used)."""
    out = {}
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        for t in COUNTED:
            rows = query_rows(tx, f"match $x isa {t}; reduce $n = count;")
            out[t] = rows[0].get("n").get_integer() if rows else 0
        # claims formed through the store but not linked to a stored candidate would mean the legacy path ran
        rows = query_rows(tx, "match $c isa claim, has candidate-id $k; not { formed-into (claim: $c); }; "
                              "reduce $n = count;")
        out["claims_with_candidate_but_no_store_link"] = rows[0].get("n").get_integer() if rows else 0
    out["database"] = memory.database
    return out


def size(memory):
    return database_bytes(memory.database)


def same_name(a, b):
    return normalise(a or "") == normalise(b or "")


@contextmanager
def timer(into, key):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        into[key] = into.get(key, 0.0) + time.perf_counter() - t0


def latency(seconds):
    s = sorted(seconds)
    if not s:
        return {"n": 0}
    return {"n": len(s), "p50": round(statistics.median(s), 5), "p95": round(s[min(len(s) - 1, int(len(s) * 0.95))], 5),
            "max": round(s[-1], 5), "total": round(sum(s), 3)}


def meta(label, part):
    return {"phase": "6D", "part": part, "run_label": label, "git": git_state(),
            "started": datetime.now(UTC).isoformat(timespec="seconds"), "peak_rss_bytes_at_start": peak_rss_bytes()}
