"""Multi-hop exploration and historical views (docs/adr/0007).

- `explore`: the neighbourhood of a referent through believed claims, one TypeDB query per hop, merging
  accepted identities, with depth and node limits (and a flag when the limit cut the walk short).
- `follow`: a chain of structured questions ("who was X's manager, and who was theirs?"), each hop answered
  by gupi.query with its own citations; only TRUE answers are followed, and unknowns are reported.
- `history`: everything recorded about a referent on both time axes: when GUPI recorded or decided it
  (transaction time) and the period each claim is about (valid time).
"""

from dataclasses import dataclass, field

from typedb.driver import TransactionType

from gupi import retrieval, typeql
from gupi.query import Question, answer
from gupi.temporal import Answer
from gupi.typedb.connection import transaction


@dataclass
class Graph:
    nodes: dict = field(default_factory=dict)   # node id (smallest member id) -> {"label", "members", "hop"}
    edges: list = field(default_factory=list)   # {"claim", "type", "roles": {role: node id}, "values", "truth"}
    truncated: bool = False
    steps: list = field(default_factory=list)


def explore(memory, referent_id, depth=2, believed_at=None, valid_at=None, max_nodes=50):
    t = believed_at or memory.clock()
    graph = Graph()
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        groups = memory.identity_groups(t, tx)

        def node(rid):
            return min(groups.get(rid, {rid}))
        start = node(referent_id)
        graph.nodes[start] = {"members": sorted(groups.get(referent_id, {referent_id})), "hop": 0}
        frontier, seen_claims = {start}, set()
        for hop in range(1, depth + 1):
            members = {m for n in frontier for m in graph.nodes[n]["members"]}
            ids = [i for i in retrieval.believed_involving(tx, members, t) if i not in seen_claims]
            graph.steps.append(f"hop {hop}: {len(ids)} believed claim(s) involving {len(frontier)} node(s)")
            seen_claims.update(ids)
            nxt = set()
            for c in retrieval.claims_by_ids(tx, ids):
                if c.type == "identity":
                    continue
                roles = {r: sorted({node(x) for x in refs}) for r, refs in c.roles.items()}
                graph.edges.append({"claim": c.id, "type": c.type, "roles": roles, "values": c.values,
                                    "truth": c.holds_at(valid_at).value if valid_at else None})
                for refs in roles.values():
                    for n in refs:
                        if n not in graph.nodes:
                            if len(graph.nodes) >= max_nodes:
                                graph.truncated = True
                                continue
                            graph.nodes[n] = {"members": sorted(groups.get(n, {n})), "hop": hop}
                            nxt.add(n)
            frontier = nxt
            if not frontier:
                break
        labels = {d["id"]: d["label"] for d in typeql.documents_for(
            tx, 'match $x isa referent, has gupi-id == $id; fetch { "id": $x.gupi-id, "label": $x.label };',
            [{"id": n} for n in graph.nodes])}
    for n, info in graph.nodes.items():
        info["label"] = labels.get(n)
    return graph


@dataclass
class Hop:
    question: Question
    result: object        # gupi.query.Result


def follow(memory, referent_id, steps, valid_at, believed_at=None, max_paths=20):
    """Follow `steps` [(claim type, from role, to role), ...] from a referent. Returns paths: lists of Hops.

    Each hop asks "who fills `to role` for this `from role` at valid_at?". Only TRUE bindings are followed;
    a hop whose answer is not TRUE ends its path there, so the caller sees exactly where knowledge stops."""
    t = believed_at or memory.clock()
    paths = [([], referent_id)]
    for claim_type, from_role, to_role in steps:
        nxt = []
        for hops, current in paths:
            if current is None:
                nxt.append((hops, None))
                continue
            q = Question(claim_type, {from_role: current, to_role: None}, valid_at, t)
            r = answer(memory, q)
            targets = [b for b in r.bindings if b.answer is Answer.TRUE] if r.answer is Answer.TRUE else []
            if not targets:
                nxt.append((hops + [Hop(q, r)], None))
            for b in targets:
                nxt.append((hops + [Hop(q, r)], b.referents[0]))
        paths = nxt[:max_paths]
    return [hops for hops, _ in paths]


@dataclass(frozen=True)
class HistoryEntry:
    at: object            # transaction time
    event: str
    claim_id: str
    description: str
    period: str           # the valid-time period the claim is about


def history(memory, referent_id, believed_at=None):
    """Both time axes for one referent (and those accepted as the same), oldest event first."""
    from gupi.review import history as claim_history
    t = believed_at or memory.clock()
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        members = memory.identity_groups(t, tx).get(referent_id, {referent_id})
        views = {}
        for m in sorted(members):
            for c in retrieval.claims_about(tx, m):
                views[c.id] = c
    entries = []
    for c in views.values():
        period = _period(c)
        what = ("NOT " if c.polarity == "negative" else "") + f"{c.type} " + ", ".join(
            f"{r}={'/'.join(v)}" for r, v in c.roles.items())
        for ev in claim_history(c):
            entries.append(HistoryEntry(ev.at, ev.kind, c.id, f"{what}: {ev.detail}", period))
        for s in c.supersessions:
            for r in s.reviews:
                entries.append(HistoryEntry(r.recorded_at, f"correction {r.verdict}", c.id,
                                            f"{what}: supersession by {s.replacement} {r.verdict} by {r.decided_by}", period))
    return sorted(entries, key=lambda e: (e.at, e.claim_id, e.event != "recorded"))  # stable: decisions keep their order


def _period(c):
    v = c.valid

    def bound(a, b):
        if a is None and b is None:
            return "?"
        return str(a.date()) if a == b else f"{a.date() if a else '?'}..{b.date() if b else '?'}"
    if c.valid_to_basis == "ongoing-at-observation":
        end = f"still true on {v.to_earliest.date()}"
    elif v.to_earliest is not None and v.to_latest is None:
        end = f"at least {v.to_earliest.date()}"
    else:
        end = bound(v.to_earliest, v.to_latest)
    return f"{bound(v.from_earliest, v.from_latest)} to {end}"
