"""Keyword search over source text: the text-only baseline (docs/adr/0007).

TypeDB's `contains` (case-insensitive in 3.14.1) selects observations received by the belief time that
contain a query word; Python keeps whole-word matches and ranks them with BM25. Only candidates are read.
The corpus size comes from a TypeDB count; average document length is taken over the candidates (an
approximation, stated here so results are not over-read). No embeddings: they are deferred.
"""

import math
import re
from dataclasses import dataclass

from typedb.driver import TransactionType

from gupi import typeql
from gupi.typedb.connection import transaction

WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
STOPWORDS = frozenset(
    "a an and are as at be by did do does for from had has have he her his in is it its of on or she "
    "that the their them they this to was were what when where which who whom why will with".split())
K1, B = 1.2, 0.75


@dataclass(frozen=True)
class Hit:
    observation_id: str
    score: float
    content: str
    source_id: str
    observed_at: object
    received_at: object
    matched: tuple


def tokens(text):
    return [w for w in WORD.findall(text.lower()) if w not in STOPWORDS]


def search(memory, text, k=5, believed_at=None):
    """The k best-matching observations GUPI had received by `believed_at` (default now)."""
    t = believed_at or memory.clock()
    words = sorted(set(tokens(text)))
    if not words:
        return []
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        docs = typeql.documents_for(tx, """
            match $o isa observation, has content $c, has received-at $r; $r <= $at; $c contains $w;
                  sourcing (source: $s, observed: $o);
            fetch { "id": $o.gupi-id, "content": $o.content, "source": $s.gupi-id,
                    "observed": $o.observed-at, "received": $o.received-at };""",
            [{"w": w, "at": t} for w in words])
        total = typeql.concept_rows(tx, "match $o isa observation, has received-at $r; $r <= $at; reduce $n = count;", {"at": t})
    n_docs = total[0].get("n").get_integer() if total else 0
    candidates = {d["id"]: d for d in docs}
    bags = {i: tokens(d["content"]) for i, d in candidates.items()}
    df = {w: sum(1 for bag in bags.values() if w in bag) for w in words}
    avgdl = sum(len(b) for b in bags.values()) / len(bags) if bags else 1.0
    hits = []
    for i, bag in bags.items():
        score, matched = 0.0, []
        for w in words:
            f = bag.count(w)
            if not f:
                continue  # `contains` matched inside another word
            matched.append(w)
            idf = math.log(1 + (n_docs - df[w] + 0.5) / (df[w] + 0.5))
            score += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * len(bag) / avgdl))
        if matched:
            d = candidates[i]
            hits.append(Hit(i, round(score, 6), d["content"], d["source"], typeql.parse_datetime(d["observed"]),
                            typeql.parse_datetime(d["received"]), tuple(matched)))
    hits.sort(key=lambda h: (-h.score, h.observation_id))
    return hits[:k]
