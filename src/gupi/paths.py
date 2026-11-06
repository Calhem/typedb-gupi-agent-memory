"""Relationship-aware evidence retrieval (docs/evaluation/phase-8).

Keyword search finds passages; relationships already stored add what the words miss. Layer 1 (no claims needed):
the turns next to a hit, and keyword hits by the speaker a question names. Original hits keep their provenance.
The speaker is only ever an ordering: filtering by speaker removes the evidence for questions that name the wrong one.

Everything is bounded and deterministic: same input and stored state, same output. Nothing here calls a model or
writes anything.
"""

import re
from dataclasses import dataclass, field

from typedb.driver import TransactionType

from gupi import evidence, typeql
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


@dataclass(frozen=True)
class Item:
    observation_id: str
    tier: str                   # "passage": raw text with no claim behind it
    reasons: tuple              # why it is here: "keyword", "neighbour", "speaker"


@dataclass
class EvidenceSet:
    items: list = field(default_factory=list)
    truncated: list = field(default_factory=list)   # which limits cut something: absence is not "nothing else"
    steps: list = field(default_factory=list)

    @property
    def ids(self):
        return [i.observation_id for i in self.items]


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
    return EvidenceSet(reasons, ["k"] if len(ordered) > budget.k else [],
                       [f"keyword: {len(hits)} hits", f"speaker: {'named' if speaker else 'none'}",
                        f"candidates: {len(ordered)}"])
