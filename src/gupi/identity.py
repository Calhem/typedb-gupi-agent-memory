"""Suggested identity resolution, never automatic merging (docs/adr/0006).

`suggest` proposes pairs of referents that may be the same thing; `record` stores each as an `identity`
claim that is a HYPOTHESIS (basis inferred, the mentions' observations as evidence, the reason attached).
Only an accepted identity claim merges referents in answers (`equivalents`), and only for belief times
from its acceptance on. Rejecting or retracting it later splits them again; earlier answers are unchanged.
"""

from dataclasses import dataclass

from typedb.driver import TransactionType

from gupi import typeql
from gupi.extraction.contract import normalise, referent_id
from gupi.records import Batch, Claim, Evidence
from gupi.status import Status
from gupi.typedb.connection import transaction

METHOD = "identity:suggest:v1"
SESSION_METHOD = "identity:session-link:v1"
MAX_GROUP = 40             # referents compared under one name; more are reported, not guessed at


@dataclass(frozen=True)
class Suggestion:
    a: str
    b: str
    kind: str
    score: float
    reason: str
    evidence: tuple  # Evidence records (one mention of each referent)


REFERENT_FETCH = """
    fetch { "id": $x.gupi-id, "kind": $k, "label": $x.label,
            "mentions": [ match reference (mention: $m, referent: $x); mentioning (container: $o, mention: $m);
                          fetch { "obs": $o.gupi-id, "start": $m.span-start, "end": $m.span-end,
                                  "contexts": [ match containment (context: $c, member: $o); fetch { "c": $c.gupi-id }; ] }; ] };"""


def _shape(d):
    contexts = {c["c"] for m in d["mentions"] for c in m["contexts"]}
    return d["id"], {"kind": d["kind"]["label"], "label": d["label"] or "", "contexts": contexts,
                     "mention": d["mentions"][0] if d["mentions"] else None}


def _candidate_groups(tx):
    """Small groups of referents that might be the same, found by TypeDB rather than by comparing all pairs:
    referents sharing an exact label, and single-word names with full names starting with them in the same
    conversation."""
    groups = []
    labels = [r.get("l").get_string() for r in typeql.concept_rows(
        tx, "match $x isa! $k, has label $l; $k sub referent; reduce $n = count groupby $l; match $n > 1;")]
    for label in labels:
        groups.append(dict(_shape(d) for d in typeql.documents(
            tx, "match $x isa! $k, has label == $l; $k sub referent;" + REFERENT_FETCH, {"l": label})))
    singles = [dict([_shape(d)]) for d in typeql.documents(
        tx, 'match $x isa! $k, has label $l; $k sub referent; $l like "^[^ ]+$";' + REFERENT_FETCH)]
    for single in singles:
        (sid, s), = single.items()
        for context in s["contexts"]:
            found = dict(_shape(d) for d in typeql.documents(tx, """
                match $c isa context, has gupi-id == $cid; containment (context: $c, member: $o);
                      mentioning (container: $o, mention: $m); reference (mention: $m, referent: $x);
                      $x isa! $k, has label $l; $k sub referent; $l contains $first;""" + REFERENT_FETCH,
                {"cid": context, "first": s["label"]}))
            found = {i: r for i, r in found.items()
                     if i != sid and normalise(r["label"]).startswith(normalise(s["label"]) + " ")}
            if found:
                groups.append({sid: s, **found})
    return groups


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
        groups = _candidate_groups(tx)
        seen = _already_considered(tx)
    out, done = [], set()
    for refs in groups:
        ids = sorted(refs)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if (a, b) in done:
                    continue
                done.add((a, b))
                suggestion = _pair(a, b, refs[a], refs[b], seen)
                if suggestion:
                    out.append(suggestion)
    return out


def _pair(a, b, ra, rb, seen):
    """A suggestion for referents a and b, or None."""
    if ra["kind"] != rb["kind"] or ra["kind"] == "unclassified" or (a, b) in seen:
        return None
    if not ra["mention"] or not rb["mention"]:
        return None  # without a mention there is no evidence to show a reviewer
    la, lb = normalise(ra["label"]), normalise(rb["label"])
    shared = ra["contexts"] & rb["contexts"]
    if la == lb and not shared:
        score, reason = 0.7, f"same name {ra['label']!r} in different conversations"
    elif shared and la.split()[:1] == lb.split()[:1] and (len(la.split()) == 1) != (len(lb.split()) == 1):
        short, full = sorted((ra["label"], rb["label"]), key=lambda n: (len(n.split()), n))
        score, reason = 0.6, f"{short!r} and {full!r}: first name matches a full name in the same conversation"
    else:
        return None
    evidence = tuple(Evidence(r["mention"]["obs"], r["mention"]["start"], r["mention"]["end"]) for r in (ra, rb))
    return Suggestion(a, b, ra["kind"], score, reason, evidence)


def record(memory, suggestions, method=METHOD):
    """Store suggestions as hypothesis identity claims. Returns their claim ids."""
    claims = tuple(Claim("identity", {"same": (s.a, s.b)}, s.evidence, values={"reason": s.reason},
                         method=method, confidence=s.score, basis="inferred") for s in suggestions)
    memory.ingest(Batch(claims=claims))
    return [c.id for c in claims]


# --- across sessions of one user ---------------------------------------------------------------------------

def participant_id(user_id, role):
    """A platform's own key for who is speaking. The same key in every session of one user IS one referent: nothing
    is inferred from a name, so there is nothing to merge. Sessions stay separate contexts."""
    return referent_id(f"user:{user_id}", "person", role)


IN_SESSION = """match $x isa context, has gupi-id == $cid; containment (context: $x, member: $o); $o has gupi-id $oid;
    mentioning (container: $o, mention: $m); reference (mention: $m, referent: $r);
    $r isa! $k, has gupi-id $rid, has label $l; $k sub referent;
    fetch { "context": $cid, "id": $rid, "label": $l, "kind": $k, "obs": $oid, "start": $m.span-start, "end": $m.span-end };"""
SPEAKERS = """match $x isa context, has gupi-id == $cid; containment (context: $x, member: $o); $o has gupi-id $oid;
    authorship (author: $r, authored: $o); $r isa! $k, has gupi-id $rid, has label $l; $k sub referent;
    fetch { "context": $cid, "id": $rid, "label": $l, "kind": $k, "obs": $oid };"""
CONNECTED = """match $a isa referent, has gupi-id == $rid; $c isa claim, links ($a), links ($n); not { $n is $a; };
    not { $c isa identity; }; $n has gupi-id $nid, has label $l; let $b in believed_claim($c, $t);
    fetch { "from": $rid, "to": $nid, "label": $l };"""


@dataclass(frozen=True)
class SessionLinks:
    linked: tuple              # Suggestions with a second signal: recorded as hypotheses, never accepted
    name_only: tuple           # (a, b, label): the same name and nothing else. Not recorded, not walked
    too_many: tuple = ()       # names with more referents than MAX_GROUP


def _same_name(a, b):
    """'exact' or 'alias' (a single word that is the first word of a fuller name), else None."""
    la, lb = normalise(a), normalise(b)
    if la == lb:
        return "exact"
    short, full = sorted((la, lb), key=lambda n: len(n.split()))
    return "alias" if len(short.split()) == 1 and full.split()[0] == short and len(full.split()) > 1 else None


def _session_groups(tx, contexts):
    """Referents named in these sessions, and each session's speakers."""
    rows = [{"cid": c} for c in sorted(set(contexts))]
    named, speakers = {}, {}
    for d in typeql.documents_for(tx, IN_SESSION, rows):
        r = named.setdefault(d["id"], {"label": d["label"], "kind": d["kind"]["label"], "contexts": set(), "mention": None})
        r["contexts"].add(d["context"])
        here = Evidence(d["obs"], d["start"], d["end"])
        if r["mention"] is None or (here.observation_id, here.span_start) < (r["mention"].observation_id, r["mention"].span_start):
            r["mention"] = here
    for d in typeql.documents_for(tx, SPEAKERS, rows):
        s = speakers.setdefault(d["id"], {"label": d["label"], "kind": d["kind"]["label"], "contexts": set(), "first": d["obs"]})
        s["contexts"].add(d["context"])
        s["first"] = min(s["first"], d["obs"])
    return named, speakers


def link_sessions(memory, contexts, record_links=True):
    """Which referents in one user's sessions may be the same, with reasons. `contexts` is that user's sessions, so
    two users are never compared. A shared name proposes a pair and never justifies one: a pair is linked only with
    a second signal, a speaker of that name in the session, or a claim tying both to something of the same name.
    Linked pairs are hypotheses for a reviewer. Nothing here accepts, merges or changes an answer."""
    at = memory.clock()
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        named, speakers = _session_groups(tx, contexts)
        seen = _already_considered(tx)
        everyone = {**{i: dict(s, mention=None) for i, s in speakers.items()}, **named}
        near = {}
        for d in typeql.documents_for(tx, CONNECTED, [{"rid": r, "t": at} for r in sorted(everyone)]):
            near.setdefault(d["from"], set()).add(normalise(d["label"]))
    groups = {}
    for rid, r in named.items():
        if r["kind"] != "unclassified":
            groups.setdefault((r["kind"], normalise(r["label"]).split()[0]), []).append(rid)
    for rid, s in speakers.items():
        for (kind, first), members in groups.items():
            if kind == s["kind"] and first == normalise(s["label"]).split()[0] and rid not in members:
                members.append(rid)
    linked, name_only, too_many = [], [], []
    for (_, first), members in sorted(groups.items()):
        if len(members) > MAX_GROUP:
            too_many.append(first)
            continue
        for i, a in enumerate(sorted(members)):
            for b in sorted(members)[i + 1:]:
                ra, rb = everyone[a], everyone[b]
                match = _same_name(ra["label"], rb["label"])
                # a pair in one session is not a link across sessions; suggest() already handles first names there
                if match is None or (a, b) in seen or (ra["contexts"] & rb["contexts"] and a not in speakers and b not in speakers):
                    continue
                signals = _signals(a, b, ra, rb, speakers, near)
                if not signals:
                    name_only.append((a, b, ra["label"]))
                    continue
                ev = tuple(everyone[x]["mention"] or _whole(memory, speakers[x]["first"]) for x in (a, b))
                linked.append(Suggestion(a, b, ra["kind"], 0.5, f"{match} name {ra['label']!r} / {rb['label']!r}: " + "; ".join(signals), ev))
    if record_links and linked:
        record(memory, linked, SESSION_METHOD)
    return SessionLinks(tuple(linked), tuple(name_only), tuple(too_many))


def _whole(memory, observation_id):
    """A speaker has no mention to cite, so the evidence is their first message in these sessions."""
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        (d,) = typeql.documents(tx, 'match $o isa observation, has gupi-id == $id; fetch { "t": $o.content };', {"id": observation_id})
    return Evidence(observation_id, 0, len(d["t"]))


def _signals(a, b, ra, rb, speakers, near):
    out = []
    for x, other in ((a, rb), (b, ra)):
        if x in speakers and speakers[x]["contexts"] & other["contexts"]:
            out.append(f"{speakers[x]['label']!r} is a speaker in a session that names them")
    shared = sorted((near.get(a, set()) & near.get(b, set())) - {normalise(ra["label"]), normalise(rb["label"])})
    if shared:
        out.append("both connected by claims to " + ", ".join(repr(n) for n in shared))
    return list(dict.fromkeys(out))


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
