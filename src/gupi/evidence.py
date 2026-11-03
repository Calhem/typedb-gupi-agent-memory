"""Evidence retrieval over a scope of contexts (docs/adr/0008), as frozen in benchmarks/config.json.

Four retrievers return ranked observation ids for a question within a scope (e.g. one conversation, or one
question's history sessions):
- keyword:    BM25 over turn text; TypeDB `contains` selects candidates in scope.
- embedding:  cosine over embeddings stored in TypeDB (optional extra).
- structured: TypeDB structure only, no text scoring: turns authored by, mentioning or naming the entities
              the question names, inside a time window read from the question; turns that are evidence for an
              extracted claim about those entities first, then newest first. Nothing when no entity is named.
- hybrid:     reciprocal rank fusion of keyword and embedding, restricted to the structured candidates when
              there are any.
"""

import math
import re
from dataclasses import dataclass, field

from typedb.driver import TransactionType

from gupi import timeexpr, typeql, vectors
from gupi.search import B, K1, tokens
from gupi.typedb.connection import transaction

IN_SCOPE = ("match $c isa context, has gupi-id == $cid; containment (context: $c, member: $o); "
            "$o isa observation, has gupi-id $oid;")
TIME_PHRASE = re.compile(
    r"\b(?:in|on|since|during|from)\s+((?:\d{1,2}\s+)?(?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)(?:\s+\d{1,2})?(?:,?\s+\d{4})?|\d{4})\b"
    r"|\b(yesterday|today|last week|last month|last year|this month|this year)\b", re.I)


@dataclass
class Ranking:
    ids: list                                   # observation ids, best first
    notes: dict = field(default_factory=dict)   # e.g. entities found, time window, candidate count


def keyword(memory, text, contexts, k=50):
    words = sorted(set(tokens(text)))
    if not words or not contexts:
        return Ranking([])
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        docs = typeql.documents_for(tx, IN_SCOPE + ' $o has content $t; $t contains $w; fetch { "id": $oid, "t": $t };',
                                    [{"cid": c, "w": w} for c in sorted(set(contexts)) for w in words])
        total = typeql.rows_for(tx, IN_SCOPE + " reduce $n = count;", [{"cid": c} for c in sorted(set(contexts))])
    n_docs = sum(r.get("n").get_integer() for r in total)
    bags = {d["id"]: tokens(d["t"]) for d in docs}
    df = {w: sum(1 for b in bags.values() if w in b) for w in words}
    avgdl = sum(map(len, bags.values())) / len(bags) if bags else 1.0
    scored = []
    for oid, bag in bags.items():
        s = sum(math.log(1 + (n_docs - df[w] + 0.5) / (df[w] + 0.5)) * f * (K1 + 1) / (f + K1 * (1 - B + B * len(bag) / avgdl))
                for w in words if (f := bag.count(w)))
        if s > 0:
            scored.append((-s, oid))
    return Ranking([oid for _, oid in sorted(scored)[:k]], {"candidates": len(bags)})


def embedding(memory, embedder, text, contexts, k=50):
    if embedder is None or not contexts:
        return Ranking([], {"embedder": None})
    return Ranking([oid for oid, _ in vectors.search(memory, embedder, text, contexts, k)])


def time_window(question, asked_at):
    """The window a question's own time phrase points to, or None (never guessed)."""
    if asked_at is None:
        return None
    for m in TIME_PHRASE.finditer(question):
        # Phase 5's frozen configuration resolved a month without a year to the past; kept for reproducibility.
        reading = timeexpr.read(m.group(1) or m.group(2), asked_at, direction="past")
        if reading:
            return reading.earliest, reading.latest
    return None


def structured(memory, question, contexts, asked_at=None, k=50):
    """Structure-only retrieval: see module docstring. Returns Ranking with notes on what it used."""
    if not contexts:
        return Ranking([])
    rows = [{"cid": c} for c in sorted(set(contexts))]
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        known = {}
        for q in (" authorship (author: $x, authored: $o); $x has label $l, has gupi-id $xid;",
                  " mentioning (container: $o, mention: $m); reference (mention: $m, referent: $x);"
                  " $x has label $l, has gupi-id $xid;"):
            for r in typeql.rows_for(tx, IN_SCOPE + q, rows):
                known.setdefault(r.get("l").get_string(), set()).add(r.get("xid").get_string())
        named = {label: ids for label, ids in known.items()
                 if re.search(rf"\b{re.escape(label)}\b", question, re.I)}
        if not named:
            return Ranking([], {"entities": [], "reason": "no entity in the question matches a referent in scope"})
        referents = sorted({i for ids in named.values() for i in ids})
        found = {}
        for q, var in ((" authorship (author: $x, authored: $o); $x has gupi-id == $rid;", "authored"),
                       (" mentioning (container: $o, mention: $m); reference (mention: $m, referent: $x);"
                        " $x has gupi-id == $rid;", "mentioned"),
                       (" evidence (supported: $cl, support: $o); $cl links ($x); $x has gupi-id == $rid;", "claim")):
            for r in typeql.rows_for(tx, IN_SCOPE + q, [{"cid": c, "rid": x} for c in sorted(set(contexts)) for x in referents]):
                found.setdefault(r.get("oid").get_string(), set()).add(var)
        for r in typeql.rows_for(tx, IN_SCOPE + " $o has content $t; $t contains $name;",
                                 [{"cid": c, "name": n} for c in sorted(set(contexts)) for n in named]):
            found.setdefault(r.get("oid").get_string(), set()).add("named")
        when = {d["id"]: typeql.parse_datetime(d["at"]) for d in typeql.documents_for(
            tx, 'match $o isa observation, has gupi-id == $id; fetch { "id": $o.gupi-id, "at": $o.observed-at };',
            [{"id": i} for i in found])} if found else {}
    window = time_window(question, asked_at)
    if window:
        found = {i: v for i, v in found.items() if when.get(i) and window[0] <= when[i] < window[1]}
    order = sorted(found, key=lambda i: ("claim" not in found[i], -(when[i].timestamp() if when.get(i) else 0), i))
    return Ranking(order[:k], {"entities": sorted(named), "window": window, "candidates": len(found)})


def hybrid(memory, embedder, question, contexts, asked_at=None, k=50, rrf_k=60, use_structure=True):
    """RRF of keyword and embedding; with use_structure, restricted to the structured candidates if any."""
    s = structured(memory, question, contexts, asked_at, k=10_000) if use_structure else Ranking([])
    lists = [keyword(memory, question, contexts, k).ids, embedding(memory, embedder, question, contexts, k).ids]
    allowed = set(s.ids)
    if allowed:
        lists = [[i for i in ranked if i in allowed] for ranked in lists]
    score = {}
    for ranked in lists:
        for rank, oid in enumerate(ranked, 1):
            score[oid] = score.get(oid, 0.0) + 1.0 / (rrf_k + rank)
    order = sorted(score, key=lambda i: (-score[i], i))
    return Ranking(order[:k], {"filtered_by_structure": bool(allowed), **{f"structured_{k_}": v for k_, v in s.notes.items()}})
