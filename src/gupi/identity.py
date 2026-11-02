"""Suggested identity resolution, never automatic merging (docs/adr/0006).

`suggest` proposes pairs of referents that may be the same thing; `record` stores each as an `identity`
claim that is a HYPOTHESIS (basis inferred, the mentions' observations as evidence, the reason attached).
Only an accepted identity claim merges referents in answers (`equivalents`), and only for belief times
from its acceptance on. Rejecting or retracting it later splits them again; earlier answers are unchanged.
"""

from dataclasses import dataclass

from typedb.driver import TransactionType

from gupi import typeql
from gupi.extraction.contract import normalise
from gupi.records import Batch, Claim, Evidence
from gupi.status import Status
from gupi.typedb.connection import transaction

METHOD = "identity:suggest:v1"


@dataclass(frozen=True)
class Suggestion:
    a: str
    b: str
    kind: str
    score: float
    reason: str
    evidence: tuple  # Evidence records (one mention of each referent)


def _referents(tx):
    """Referents with their kind, label, the contexts they are mentioned in, and one mention each."""
    found = {}
    for d in typeql.documents(tx, """
            match $x isa! $k; $k sub referent; $x has gupi-id $id;
            fetch { "id": $id, "kind": $k, "label": $x.label,
                    "mentions": [ match reference (mention: $m, referent: $x); mentioning (container: $o, mention: $m);
                                  fetch { "obs": $o.gupi-id, "start": $m.span-start, "end": $m.span-end,
                                          "contexts": [ match containment (context: $c, member: $o); fetch { "c": $c.gupi-id }; ] }; ] };"""):
        contexts = {c["c"] for m in d["mentions"] for c in m["contexts"]}
        found[d["id"]] = {"kind": d["kind"]["label"], "label": d["label"] or "", "contexts": contexts,
                          "mention": d["mentions"][0] if d["mentions"] else None}
    return found


def _already_considered(tx):
    """Referent pairs that already have an identity claim, whatever its status (rejected ones are not re-suggested)."""
    pairs = set()
    for d in typeql.documents(tx, 'match $i isa identity; fetch { "ids": [ match $i links (same: $x); fetch { "id": $x.gupi-id }; ] };'):
        ids = sorted(x["id"] for x in d["ids"])
        if len(ids) == 2:
            pairs.add(tuple(ids))
    return pairs


def suggest(memory):
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        refs = _referents(tx)
        seen = _already_considered(tx)
    out = []
    ids = sorted(refs)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ra, rb = refs[a], refs[b]
            if ra["kind"] != rb["kind"] or ra["kind"] == "unclassified" or (a, b) in seen:
                continue
            if not ra["mention"] or not rb["mention"]:
                continue  # without a mention there is no evidence to show a reviewer
            la, lb = normalise(ra["label"]), normalise(rb["label"])
            shared = ra["contexts"] & rb["contexts"]
            if la == lb and not shared:
                score, reason = 0.7, f"same name {ra['label']!r} in different conversations"
            elif shared and (la.split()[:1] == lb.split()[:1]) and (len(la.split()) == 1) != (len(lb.split()) == 1):
                short, full = sorted((ra["label"], rb["label"]), key=lambda n: (len(n.split()), n))
                score, reason = 0.6, f"{short!r} and {full!r}: first name matches a full name in the same conversation"
            else:
                continue
            evidence = tuple(Evidence(r["mention"]["obs"], r["mention"]["start"], r["mention"]["end"]) for r in (ra, rb))
            out.append(Suggestion(a, b, ra["kind"], score, reason, evidence))
    return out


def record(memory, suggestions):
    """Store suggestions as hypothesis identity claims. Returns their claim ids."""
    claims = tuple(Claim("identity", {"same": (s.a, s.b)}, s.evidence, values={"reason": s.reason},
                         method=METHOD, confidence=s.score, basis="inferred") for s in suggestions)
    memory.ingest(Batch(claims=claims))
    return [c.id for c in claims]


def equivalents(identity_claims, at):
    """Groups of referents that accepted identity claims (at transaction time `at`) say are the same."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for c in identity_claims:
        if c.status_at(at) is Status.ACCEPTED:
            a, b = c.roles["same"]
            parent[find(a)] = find(b)
    groups = {}
    for x in list(parent):
        groups.setdefault(find(x), set()).add(x)
    return {x: frozenset(g) for g in groups.values() for x in g}
