"""Relationship-aware evidence retrieval (docs/evaluation/phase-8).

Keyword search finds passages; relationships already stored add what the words miss. Layer 1 (no claims needed):
the turns next to a hit, and keyword hits by the speaker a question names. Original hits keep their provenance.
The speaker is only ever an ordering: filtering by speaker removes the evidence for questions that name the wrong one.

Layer 2 (where claims exist): one or two hops through believed claims, starting from the claims behind the top hits
and from names in the question. A path is a list of separately qualified hops, never one fact: connectivity says
nothing about time, so each pair of hops gets an overlap label from the existing temporal model (answering_v2).

Everything is bounded and deterministic: same input and stored state, same output. Nothing here calls a model or
writes anything, and nothing is promoted: uncertain material comes back labelled.
"""

import json
import re
from dataclasses import dataclass, field, replace
from datetime import timedelta

from typedb.driver import TransactionType

from gupi import evidence, retrieval, typeql
from gupi.answering_v2 import classify
from gupi.qualification import qualifiers
from gupi.search import tokens
from gupi.temporal import Answer
from gupi.typedb.connection import transaction

MEMBERS = evidence.IN_SCOPE + (' $o has observed-at $at, has received-at $r; '
                               'fetch { "id": $oid, "at": $o.observed-at, "received": $o.received-at };')
AUTHORS = evidence.IN_SCOPE + (' authorship (author: $x, authored: $o); $x has gupi-id $xid, has label $l; '
                               'fetch { "id": $oid, "author": $xid, "label": $l };')


@dataclass(frozen=True)
class Budget:
    k: int = 10                 # evidence items returned, the same for every configuration compared
    pool: int = 50              # keyword hits considered
    keep: int = 3               # top keyword hits that always stay in place
    window: int = 1             # turns either side of a hit
    seeds: int = 5              # top keyword hits whose claims start a walk
    hops: int = 2               # never more: there is no recursion
    max_paths: int = 50         # paths kept, after sorting
    hub: int = 100              # a referent with more claims is not crossed unless the question names it


@dataclass(frozen=True)
class Item:
    observation_id: str
    tier: str                   # accepted, qualified, unresolved, or passage (raw text, no claim behind it)
    reasons: tuple              # why it is here: "keyword", "neighbour", "speaker", "path"
    notes: tuple = ()           # qualifications, in words
    originators: tuple = ()     # who asserted the claims behind it, where that is not the author
    text: str | None = None
    observed_at: str | None = None


@dataclass
class EvidenceSet:
    items: list = field(default_factory=list)
    paths: list = field(default_factory=list)
    ambiguous: list = field(default_factory=list)   # names matching people not accepted as the same
    truncated: list = field(default_factory=list)   # which limits cut something: absence is not "nothing else"
    steps: list = field(default_factory=list)

    @property
    def ids(self):
        return [i.observation_id for i in self.items]


@dataclass(frozen=True)
class Hop:
    claim_id: str
    start: str                  # referent ids
    end: str
    observations: tuple         # the evidence for this hop; a hop with none is never returned
    relation: str               # claim type, with the predicate for a generic statement
    tier: str                   # accepted or qualified
    notes: tuple = ()


@dataclass(frozen=True)
class Path:
    hops: tuple
    labels: tuple               # entities along the path, in order
    overlap: str | None         # two hops only: confirmed, presumed, none or unknown
    bridging: bool              # both ends are anchors, not just the start


# --- pure ordering: no database, so every rule can be tested directly ------------------------------------

def nearby(turn, sequence, position, window):
    """Turns within `window` of `turn` in its own session, nearest first, later before earlier."""
    seq, at, out = sequence[turn], position[turn], []
    for d in range(1, window + 1):
        out += [seq[p] for p in (at + d, at - d) if 0 <= p < len(seq)]
    return out


def with_neighbours(hits, sequence, position, keep, window):
    """The top `keep` hits in place, then each hit followed by its neighbours."""
    out = list(hits[:keep])
    for hit in hits:
        for turn in ([hit] if hit not in out else []) + (nearby(hit, sequence, position, window) if hit in sequence else []):
            if turn not in out:
                out.append(turn)
    return out


def speaker_first(hits, by_speaker):
    """The speaker's hits first, then the rest: nothing is dropped."""
    return [h for h in hits if h in by_speaker] + [h for h in hits if h not in by_speaker]


def interleave(first, second):
    """Alternate two rankings, `first` leading, keeping each item's earliest place."""
    out = []
    for pair in zip(first, second):
        for item in pair:
            if item not in out:
                out.append(item)
    return out


def named_speaker(question, labels):
    """The author ids of the one speaker the question names; empty if none, or several, are named."""
    named = [ids for label, ids in sorted(labels.items()) if re.search(rf"\b{re.escape(label)}\b", question)]
    return named[0] if len(named) == 1 else frozenset()


# --- retrieval --------------------------------------------------------------------------------------------

def _scope(memory, contexts, believed_at):
    """Each context's turns in order, and who wrote what, as of `believed_at`. One query per kind of fact."""
    rows = [{"cid": c} for c in sorted(set(contexts))]
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        turns = [(c, d) for c in rows for d in typeql.documents_for(tx, MEMBERS, [c])]
        authors = [(d["id"], d["author"], d["label"]) for d in typeql.documents_for(tx, AUTHORS, rows)]
    known = {}
    for c, d in turns:
        at, received = typeql.parse_datetime(d["at"]), typeql.parse_datetime(d["received"])
        if believed_at is None or received <= believed_at:
            known.setdefault(c["cid"], {})[d["id"]] = at
    sequence, position = {}, {}
    for members in known.values():
        ordered = sorted(members, key=lambda oid: (members[oid], oid))   # ties break on id: repeatable
        for p, oid in enumerate(ordered):
            sequence[oid], position[oid] = ordered, p
    by_author, labels = {}, {}
    for oid, author, label in authors:
        if oid in sequence:
            by_author.setdefault(author, set()).add(oid)
            labels.setdefault(label, set()).add(author)
    return sequence, position, by_author, {k: frozenset(v) for k, v in labels.items()}


def conversational(memory, question, contexts, budget=Budget(), believed_at=None):
    """Keyword hits plus conversational structure, cut to `budget.k`. See the module docstring."""
    hits = evidence.keyword(memory, question, contexts, budget.pool).ids
    if not hits:
        return EvidenceSet(steps=["keyword: no hits"])
    sequence, position, by_author, labels = _scope(memory, contexts, believed_at)
    hits = [h for h in hits if h in sequence]                  # received by the belief time
    speaker = named_speaker(question, labels)
    spoken = set().union(*[by_author.get(a, set()) for a in sorted(speaker)]) if speaker else set()
    windowed = with_neighbours(hits, sequence, position, budget.keep, budget.window)
    ordered = interleave(speaker_first(hits, spoken), windowed)
    ordered += [t for t in windowed if t not in ordered]       # interleaving stops at the shorter list
    keyword_hits, reasons = set(hits), []
    for oid in ordered[:budget.k]:
        why = ("keyword",) if oid in keyword_hits else ("neighbour",)
        reasons.append(Item(oid, "passage", why + (("speaker",) if oid in spoken else ())))
    return EvidenceSet(reasons, truncated=["k"] if len(ordered) > budget.k else [],
                       steps=[f"keyword: {len(hits)} hits", f"speaker: {'named' if speaker else 'none'}",
                        f"candidates: {len(ordered)}"])


# --- layer 2: claim paths ---------------------------------------------------------------------------------

SEED_REFERENTS = ("match $o isa observation, has gupi-id == $oid; evidence (supported: $c, support: $o); "
                  "$c links ($x); $x isa referent, has gupi-id $xid; not { $c isa identity; }; "
                  "let $b in believed_claim($c, $t); select $xid;")
HOP = ("match $a isa referent, has gupi-id == $rid, has gupi-id $aid; $c isa claim, links ($a), has gupi-id $cid; "
       "$c links ($n); not { $n is $a; }; $n isa referent, has gupi-id $nid; not { $c isa identity; }; "
       "let $b in believed_claim($c, $t); select $aid, $cid, $nid;")
REFERENT_LABELS = ("match $c isa context, has gupi-id == $cid; containment (context: $c, member: $o); "
                   "mentioning (container: $o, mention: $m); reference (mention: $m, referent: $x); "
                   "$x has gupi-id $xid, has label $l; select $xid, $l;")
OBSERVATION_CLAIMS = ("match $o isa observation, has gupi-id == $oid, has gupi-id $ob; "
                      "evidence (supported: $c, support: $o); $c has gupi-id $cid; select $ob, $cid;")
OBSERVATION_DECISIONS = """match $o isa observation, has gupi-id == $oid; candidate-of (candidate: $m, observation: $o);
    $d isa formation-decision, links (decided: $m), has recorded-at $at; $at <= $t;
    fetch { "observation": $o.gupi-id, "candidate": $m.gupi-id, "out": $d.formation-outcome, "at": $at };"""
AUTHOR_OF = ("match $o isa observation, has gupi-id == $oid, has gupi-id $ob; authorship (author: $x, authored: $o); "
             "$x has gupi-id $xid; select $ob, $xid;")
TEXT = 'match $o isa observation, has gupi-id == $oid; fetch { "id": $o.gupi-id, "text": $o.content, "at": $o.observed-at };'
THREAD_RETRACTIONS = """match $o isa observation, has gupi-id == $oid; containment (context: $x, member: $o);
    containment (context: $x, member: $o2); candidate-of (candidate: $m, observation: $o2);
    $m has candidate-payload $p; $p contains "retracts"; $o2 has gupi-id $oid2;
    fetch { "for": $o.gupi-id, "observation": $oid2, "candidate": $m.gupi-id, "payload": $p, "at": $o2.observed-at,
            "decisions": [ match formation-decision (decided: $m), has formation-outcome $d, has recorded-at $w;
                           fetch { "out": $d, "at": $w }; ] };"""


def _strings(rows, *names):
    return [tuple(r.get(n).get_string() for n in names) for r in rows]


def _named(tx, question, contexts, groups):
    """Referents the question names, as groups: exact labels, whole words, longest first. A label matching people
    not accepted as the same stays several groups and is reported; nothing merges here."""
    rows = typeql.rows_for(tx, REFERENT_LABELS, [{"cid": c} for c in sorted(set(contexts))])
    by_label = {}
    for rid, label in _strings(rows, "xid", "l"):
        by_label.setdefault(label, set()).add(rid)
    named, ambiguous, taken = [], [], question
    for label in sorted(by_label, key=lambda s: (-len(s), s)):
        if label != "I" and re.search(rf"\b{re.escape(label)}\b", taken, re.I):
            taken = re.sub(rf"\b{re.escape(label)}\b", " ", taken, flags=re.I)
            found = sorted({frozenset(groups.get(r, {r})) for r in by_label[label]}, key=sorted)
            named += found
            if len(found) > 1:
                ambiguous.append(label)
    return named, ambiguous


def _walk(tx, starts, named, groups, t, budget):
    """Paths from each start group: [[(claim, from, to), ...]] sorted, plus any limit that cut something."""
    def group(r):
        return frozenset(groups.get(r, {r}))

    def edges(members):
        rows = typeql.rows_for(tx, HOP, [{"rid": r, "t": t} for r in sorted(members)]) if members else []
        out = {}
        for rid, cid, nid in _strings(rows, "aid", "cid", "nid"):
            out.setdefault(group(rid), []).append((cid, rid, nid))
        return out

    first = edges({r for g in starts for r in g})
    second = edges({m for es in first.values() for _, _, n in es for m in group(n)}) if budget.hops > 1 else {}
    paths, cut = [], []
    for start in sorted(starts, key=sorted):
        for e1 in sorted(first.get(start, [])):
            middle = group(e1[2])
            if middle == start:
                continue
            paths.append((e1,))
            if len(second.get(middle, ())) > budget.hub and middle not in named:
                cut.append("hub")
                continue
            for e2 in sorted(second.get(middle, [])):
                if e2[0] != e1[0] and group(e2[2]) not in (start, middle):
                    paths.append((e1, e2))
    return paths, sorted(set(cut))


def _times(views):
    """Points that bracket these claims' stated times: where a boundary window starts and ends. No date is invented."""
    points = []
    for c in views:
        v = c.valid
        lo, hi = (v.from_earliest, v.from_latest) if v.from_earliest or v.from_latest else (v.to_earliest, v.to_latest)
        points += [x for x in (lo, hi - timedelta(seconds=1) if hi else None) if x is not None]
    return sorted(set(points))


def overlap_label(a, b):
    """Did proposition `a` hold during `b`'s stated time? From the existing model, over all of each proposition's
    believed claims. Connectivity alone is never enough: with no stated time the answer is unknown."""
    a, b, label = [c for c in a if c.polarity != "negative"], list(b), "unknown"
    points = _times(b)
    if not points:
        a, b, points = b, a, _times(a)
    if not points:
        return label
    answers = {classify(a, p, True).answer for p in points}
    if answers == {Answer.TRUE}:
        return "confirmed"
    if answers == {Answer.FALSE}:
        return "none"
    if answers <= {Answer.TRUE, Answer.PRESUMED}:
        return "presumed"
    return label


def _proposition(view):
    return view.proposition_key, view.values.get("predicate-text")   # statements share a key across predicates


def _disputed(claims):
    return len({(c.valid.from_earliest, c.valid.from_latest, c.valid.to_earliest, c.valid.to_latest) for c in claims
                if c.valid.from_earliest or c.valid.to_earliest}) > 1 and not any(c.valid.to_latest for c in claims)


def _hop(edge, view, family):
    notes = [f"qualified: {q}" for q in qualifiers(view)]
    if _disputed(family):
        notes.append("sources disagree on the date")
    relation = view.values.get("predicate-text") or view.type
    return Hop(view.id, edge[1], edge[2], tuple(e.observation_id for e in view.evidence), relation,
               "qualified" if notes else "accepted", tuple(notes))


def _rank(paths, words, anchored):
    """Paths joining two anchors first, then most question words, then shortest. Ends in ids: repeatable."""
    def key(p):
        text = " ".join(p.labels + tuple(h.relation for h in p.hops)).lower()
        return (not p.bridging, -len(words & set(tokens(text))), len(p.hops), [h.claim_id for h in p.hops])
    return sorted(paths, key=key)


def _pending(view, retractions, authors):
    """Observations with an undecided retraction that may concern this claim: same thread, same author, later, and
    naming nothing that rules it out. The claim is unchanged: this is a note, never a verdict."""
    out = []
    observed = {e.observation_id: e.observed_at for e in view.evidence}
    for oid, r in retractions:
        if oid not in observed or typeql.parse_datetime(r["at"]) <= observed[oid]:
            continue
        latest = max(r["decisions"], key=lambda d: d["at"])["out"] if r["decisions"] else None
        if latest != "review" or authors.get(r["observation"]) != authors.get(oid):
            continue
        out.append(r)
    return out


def _about(payload):
    (candidate,) = json.loads(payload)["candidates"]
    values = dict(tuple(v) for v in candidate.get("values", ()))
    return set(re.findall(r"\b[A-Z][\w'-]+", values.get("object-text", "")))


def _annotate(tx, ids_, t, labels_of):
    """Tier, notes and originators for each observation, read from what is stored. Raw text stays a passage."""
    rows = [{"oid": i} for i in ids_]
    claims = {}
    for oid, cid in _strings(typeql.rows_for(tx, OBSERVATION_CLAIMS, rows), "ob", "cid") if rows else []:
        claims.setdefault(oid, set()).add(cid)
    views = {v.id: v for v in retrieval.claims_by_ids(tx, {c for cs in claims.values() for c in cs})}
    believed = retrieval.believed_among(tx, list(views), t)
    decisions = {}                       # (observation, candidate) -> latest (time, outcome)
    for d in typeql.documents_for(tx, OBSERVATION_DECISIONS, [{"oid": i, "t": t} for i in ids_]) if rows else []:
        key = (d["observation"], d["candidate"])
        decisions[key] = max(decisions.get(key, ("", "")), (d["at"], d["out"]))
    retractions = [(d["for"], d) for d in typeql.documents_for(tx, THREAD_RETRACTIONS, rows)] if rows else []
    wanted = sorted({r["observation"] for _, r in retractions} | set(ids_))
    authors = dict(_strings(typeql.rows_for(tx, AUTHOR_OF, [{"oid": i} for i in wanted]), "ob", "xid")) if wanted else {}
    asserters = retrieval.asserters(tx, list(views))
    names = labels_of(set(asserters.values()))
    out = {}
    for oid in ids_:
        mine = [views[c] for c in sorted(claims.get(oid, ())) if c in views and views[c].type != "identity"]
        held = [v for v in mine if v.id in believed]
        open_ = sorted(o for (i, _), (_, o) in decisions.items() if i == oid and o in ("review", "withheld"))
        notes = [f"qualified: {q}" for v in held for q in qualifiers(v)]
        notes += [f"not accepted: {o}" for o in open_]
        for v in held:
            for r in _pending(v, retractions, authors):
                about = _about(r["payload"])
                players = {w for roles in v.roles.values() for x in roles for w in (labels_of({x}).get(x) or "").split()}
                if not about or about & players:
                    notes.append(f"pending retraction: {r['observation']}")
        tier = "unresolved" if open_ else "qualified" if held and notes else "accepted" if held else "passage"
        out[oid] = (tier, tuple(dict.fromkeys(notes)),
                    tuple(sorted({names[asserters[v.id]] for v in held if v.id in asserters and names.get(asserters[v.id])})))
    return out


def _qualified(hop, info):
    """A hop is never more certain than its evidence: a note on an observation applies to the hop."""
    notes = tuple(n for o in hop.observations for n in info.get(o, ("", ()))[1] if n.startswith(("pending", "not accepted")))
    return replace(hop, tier="qualified", notes=tuple(dict.fromkeys(hop.notes + notes))) if notes else hop


def render(found):
    """Plain text for an answering model: every qualification is in the words, since consumers may read only text."""
    def line(i):
        extras = list(i.notes) + [f"asserted by {o}" for o in i.originators]
        return f"[{str(i.observed_at)[:10]}] {i.text}" + (f" ({i.tier}: {'; '.join(extras)})" if extras else "")
    lines = [line(i) for i in found.items]
    for p in found.paths[:3]:
        steps = " -> ".join(f"{a} [{h.relation}{', ' + h.tier if h.tier != 'accepted' else ''}] {b}"
                            for a, h, b in zip(p.labels, p.hops, p.labels[1:]))
        if len(p.hops) > 1:
            steps += f"; these held at the same time: {p.overlap}"
        lines.append("Connection, not a stated fact: " + steps)
    lines += [f"{n!r} may be several people; nothing here merges them." for n in found.ambiguous]
    return lines


def retrieve(memory, question, contexts, budget=Budget(), believed_at=None):
    """Conversational evidence plus claim paths, ranked and cut to `budget.k`. See the module docstring."""
    t = believed_at or memory.clock()
    base = conversational(memory, question, contexts, replace(budget, k=budget.pool), believed_at)
    if not base.items:
        return base
    seeds = [i.observation_id for i in base.items if i.reasons[0] == "keyword"][:budget.seeds]
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        groups = memory.identity_groups(t, tx)

        def labels_of(referents):
            docs = typeql.documents_for(tx, 'match $x isa referent, has gupi-id == $id; fetch { "id": $x.gupi-id, "l": $x.label };',
                                        [{"id": r} for r in sorted(referents)]) if referents else []
            return {d["id"]: d["l"] for d in docs}

        named, ambiguous = _named(tx, question, contexts, groups)
        seeded = {r for r, in _strings(typeql.rows_for(tx, SEED_REFERENTS, [{"oid": o, "t": t} for o in seeds]), "xid")} if seeds else set()
        starts = list(dict.fromkeys(named + sorted({frozenset(groups.get(r, {r})) for r in seeded}, key=sorted)))
        edges, cut = _walk(tx, starts, set(named), groups, t, budget)
        views = {v.id: v for v in retrieval.claims_by_ids(tx, {e[0] for p in edges for e in p})}
        keys = {v.proposition_key for v in views.values()}
        recorded = retrieval.claims_by_ids(tx, retrieval.recorded_with_keys(tx, keys, t))
        held = retrieval.believed_among(tx, [c.id for c in recorded], t)
        families = {}
        for c in recorded:
            if c.id in held:
                families.setdefault(_proposition(c), []).append(c)
        labels = labels_of({x for p in edges for e in p for x in e[1:]})
        anchored = set(starts)
        paths = []
        for p in edges:
            if not all(views.get(e[0]) and views[e[0]].evidence for e in p):
                continue                                               # a hop with no evidence is never returned
            hops = tuple(_hop(e, views[e[0]], families.get(_proposition(views[e[0]]), [views[e[0]]])) for e in p)
            over = overlap_label(*[families.get(_proposition(views[h.claim_id]), []) for h in hops]) if len(hops) == 2 else None
            ends = (frozenset(groups.get(p[0][1], {p[0][1]})), frozenset(groups.get(p[-1][2], {p[-1][2]})))
            walked = (labels.get(p[0][1]),) + tuple(labels.get(e[2]) for e in p)
            paths.append(Path(hops, tuple(str(x) for x in walked), over, ends[1] in anchored and ends[0] != ends[1]))
        ranked = _rank(paths, set(tokens(question)), anchored)
        if len(ranked) > budget.max_paths:
            cut.append("max_paths")
            ranked = ranked[:budget.max_paths]
        by_proposition = {k: [o for c in v for o in (e.observation_id for e in c.evidence)] for k, v in families.items()}
        from_paths = []
        for path in ranked:
            for h in path.hops:
                from_paths += list(h.observations) + by_proposition.get(_proposition(views[h.claim_id]), [])
        from_paths = list(dict.fromkeys(from_paths))
        conversation = base.ids
        order = list(conversation[:budget.keep])
        rest = [i for i in interleave(from_paths, conversation[budget.keep:]) + from_paths + conversation]
        order = list(dict.fromkeys(order + rest))
        chosen = order[:budget.k]
        info = _annotate(tx, sorted(set(chosen) | {o for p in ranked for h in p.hops for o in h.observations}), t, labels_of)
        ranked = [replace(p, hops=tuple(_qualified(h, info) for h in p.hops)) for p in ranked]
        texts = {d["id"]: d for d in typeql.documents_for(tx, TEXT, [{"oid": o} for o in chosen])} if chosen else {}
    earlier = {i.observation_id: i.reasons for i in base.items}
    items = [Item(o, info[o][0], earlier.get(o, ()) + (("path",) if o in from_paths else ()), info[o][1], info[o][2],
                  texts[o]["text"], texts[o]["at"]) for o in chosen]
    return EvidenceSet(items, ranked, ambiguous, sorted(set(cut + (["k"] if len(order) > budget.k else []))),
                       base.steps + [f"anchors: {len(named)} named, {len(seeded)} from seeds", f"paths: {len(ranked)}"])
