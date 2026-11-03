"""Answer semantics v2: evidence first, then a decision table at one instant (docs/adr/0009,
docs/specialist/v2-truth-semantics.md).

The input is what TypeDB has already selected: the claims about one proposition that are believed at the
belief time (the cutoff of ADR 0006, which is also where corrections act), the valid time v, and whether
anything about the proposition had been recorded by then. Each claim's valid time and polarity give
evidence items:

- positive span: a positive claim's certain period [from-latest, to-earliest); a claim whose end is open
  ("still true at o", to-earliest without to-latest) is also certainly true at o itself (a point, Q5)
- negation: the same coverage for a negative claim. It is never a boundary and never continued (Q4).
- start window [from-earliest, from-latest) and end window [to-earliest, to-latest) of positive claims;
  statements about the same boundary are combined first (Q6)
- termination: a positive claim's end. Negative from its latest bound until a later start may have begun,
  i.e. that start's earliest bound (Q3). A start is never negative evidence (Q1).

Missing evidence is never negative evidence. Source reliability and authority play no part (Q8).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from gupi.temporal import Answer

LOW = datetime.min.replace(tzinfo=timezone.utc)
HIGH = datetime.max.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class Basis:
    kind: str        # direct-span, direct-point, joined-spell, negation, termination-continuing, conflict,
    claims: tuple    # window, no-coverage, not-recorded, not-believed; `claims` are the deciding claim ids


@dataclass(frozen=True)
class Classification:
    answer: Answer
    basis: Basis
    explanation: str
    notes: tuple = field(default=())


@dataclass(frozen=True)
class _Boundary:
    kind: str        # "start" or "end"
    lo: datetime     # the boundary lies in [lo, hi)
    hi: datetime
    claims: tuple    # every claim stating this boundary
    sharp: tuple     # the claims that set `hi` (cited for terminations) or `lo` (for starts' joins)
    competing: bool = False   # statements about the same boundary with disjoint windows (Q2, Q9)
    rivals: tuple = ()        # for a competing start: every start statement in its group (Q9)


def classify(believed, at, anything_recorded, bounding=()):
    """Classify instant `at`. `believed`: claims believed at the belief time that match the question;
    `bounding`: believed claims about the same relationship that lack a filtered value. They contribute
    only negative evidence (their terminations and negations), as in v1."""
    if not anything_recorded:
        return Classification(Answer.NOT_YET_KNOWN, Basis("not-recorded", ()),
                              "NOT_YET_KNOWN: nothing about this had been recorded by the belief time.")
    claims = list(believed) + [c for c in bounding if c not in believed]
    if not claims:
        return Classification(Answer.UNKNOWN, Basis("not-believed", ()),
                              "UNKNOWN: claims were recorded, but none is believed at the belief time.")
    positive = [c for c in believed if c.polarity != "negative"]
    negative = [c for c in claims if c.polarity == "negative"]
    starts, ends, notes = _merge_all([b for c in positive if (b := _start(c))],
                                     [b for c in claims if c.polarity != "negative" and (b := _end(c))])
    notes = list(notes)

    pos = [c for c in positive if _covers(c, at)]
    neg_negations = [c for c in negative if _covers(c, at)]
    neg_terminations = [e for e in ends if _terminated(e, starts, at)]
    contested_ends = _between_competing_ends(ends, at)

    if pos and (neg_negations or neg_terminations):
        others = sorted({c.id for c in neg_negations} | {i for e in neg_terminations for i in e.sharp})
        return _result(Answer.CONTESTED, "conflict", [c.id for c in pos] + others, notes,
                       f"CONTESTED: {_ids(pos)} say it held at {_d(at)}, and {', '.join(others)} that it did not.")
    disputed = _competing_starts(starts, ends, positive, pos, at)
    if disputed:
        support, against, imprecise = disputed
        if support and against:
            return _result(Answer.CONTESTED, "conflict", support + against, notes,
                           f"CONTESTED: the start date is disputed. {', '.join(support)} place(s) the start before "
                           f"{_d(at)} with the period continuing past it, while {', '.join(against)} date(s) the start "
                           f"of the same period after {_d(at)}. Neither start is preferred.")
        if support and imprecise:
            return _result(Answer.UNKNOWN, "window", support + imprecise, notes,
                           f"UNKNOWN: the start date is disputed. {', '.join(support)} place(s) the start before "
                           f"{_d(at)}, but the date given by {', '.join(imprecise)} is too imprecise to say whether it "
                           f"was before or after {_d(at)}. The true start is not assumed to lie between them.")
        if support:
            notes.append(f"the start date is disputed ({', '.join(_window_text(s) for s in starts if s.rivals)}); "
                         f"every account places the start by {_d(at)}, and none is preferred")
    if pos:
        spans = [c for c in pos if _span(c) and _span(c)[0] <= at < _span(c)[1]]
        kind = "direct-span" if spans else "direct-point"
        return _result(Answer.TRUE, kind, [c.id for c in pos], notes,
                       f"TRUE: {_ids(pos)} directly cover {_d(at)}.")
    if contested_ends:
        return _result(Answer.CONTESTED, "conflict", contested_ends, notes,
                       f"CONTESTED: {', '.join(contested_ends)} state different ends; {_d(at)} lies between them.")
    if neg_negations:
        return _result(Answer.FALSE, "negation", [c.id for c in neg_negations], notes,
                       f"FALSE: {_ids(neg_negations)} explicitly state it did not hold at {_d(at)}.")
    if neg_terminations:
        e = max(neg_terminations, key=lambda b: b.hi)
        return _result(Answer.FALSE, "termination-continuing", list(e.sharp), notes,
                       f"FALSE: recorded as ended by {_d(e.hi)} ({', '.join(e.sharp)}), with no later start or "
                       f"correction recorded by the belief time. This is a default, not an observation at {_d(at)}.")
    windows = [b for b in starts + ends if b.lo <= at < b.hi]
    if windows:
        ids = sorted({i for b in windows for i in b.claims})
        return _result(Answer.UNKNOWN, "window", ids, notes,
                       f"UNKNOWN: {_d(at)} lies inside the uncertain date of {', '.join(ids)}.")
    joined = _joined(starts, ends, positive, at)
    if joined:
        s, target = joined
        return _result(Answer.PRESUMED, "joined-spell", list(s.sharp) + list(target), notes,
                       f"PRESUMED: inside a period joined from {', '.join(s.sharp)} to {', '.join(target)}, "
                       "which no single claim covers; assumes no unrecorded break.")
    return _result(Answer.UNKNOWN, "no-coverage", [], notes, f"UNKNOWN: no believed evidence covers {_d(at)}.")


# --- evidence items -------------------------------------------------------------------------------------

def _span(c):
    """The certain period [from-latest, to-earliest), or None."""
    v = c.valid
    if v.from_latest is None or v.to_earliest is None or v.from_latest >= v.to_earliest:
        return None
    return v.from_latest, v.to_earliest


def _point(c):
    """The instant a claim with an open end is certainly true at (to-earliest without to-latest), or None."""
    v = c.valid
    return v.to_earliest if v.to_earliest is not None and v.to_latest is None else None


def _covers(c, at):
    span = _span(c)
    return bool(span and span[0] <= at < span[1]) or _point(c) == at


def _start(c):
    v = c.valid
    if v.from_earliest is None and v.from_latest is None:
        return None
    return _Boundary("start", v.from_earliest or LOW, v.from_latest or HIGH, (c.id,), (c.id,))


def _end(c):
    v = c.valid
    if v.to_latest is None:
        return None
    return _Boundary("end", v.to_earliest or LOW, v.to_latest, (c.id,), (c.id,))


def _merge_all(starts, ends):
    """Merge statements about the same boundary: consecutive boundaries of one kind, with none of the
    other kind between them (Q6). Overlapping windows narrow to their intersection; the claims that set the
    narrowed latest bound are the ones cited. Disjoint ones compete and are kept apart, each claim with its
    own window: for ends that is Q2 (CONTESTED between them); for starts, Q9 (_competing_starts)."""
    order = sorted(starts + ends, key=lambda b: (b.lo, b.hi, b.kind != "end"))
    groups, notes = [], []
    for b in order:
        if groups and groups[-1][0].kind == b.kind:
            groups[-1].append(b)
        else:
            groups.append([b])
    merged = []
    for g in groups:
        if len(g) == 1:
            merged.append(g[0])
            continue
        lo, hi = max(b.lo for b in g), min(b.hi for b in g)
        claims = tuple(sorted({i for b in g for i in b.claims}))
        if lo < hi or (lo == hi and any(b.lo == b.hi for b in g)):  # an exact bound inside a window
            sharp = tuple(sorted({i for b in g for i in b.sharp if b.hi == hi}))
            merged.append(_Boundary(g[0].kind, lo, hi, claims, sharp))
        elif g[0].kind == "end":
            merged += [_Boundary("end", b.lo, b.hi, b.claims, b.sharp, competing=True) for b in g]  # Q2
        else:
            group = tuple(b.claims[0] for b in g)
            merged += [_Boundary("start", b.lo, b.hi, b.claims, b.sharp, True, group) for b in g]  # Q9
    return [b for b in merged if b.kind == "start"], [b for b in merged if b.kind == "end"], notes


def _terminated(end, starts, at):
    """Is `at` inside this termination's negative range: from its latest bound until a later start may
    have begun? A start counts as later when its earliest bound is not before the end's earliest bound."""
    later = [s.lo for s in starts if s.lo >= end.lo]
    return end.hi <= at < min(later, default=HIGH)


def _competing_starts(starts, ends, positive, pos, at):
    """Q9: start statements about the same period that disagree (disjoint windows, no end between them).

    Each is judged on its own, with its own window, for the instant `at`:
    - supports: it certainly started by `at`, and the period is evidenced to continue past it (a later end,
      point or span with no termination between), or a claim directly covers `at`
    - contradicts: its whole window is after `at`, i.e. it dates the start of the same period later
    - imprecise: its window contains `at`
    - silent: it started by `at`, but nothing shows the period continuing
    Returns (supporting, contradicting, imprecise) claim ids, or None when there is no such dispute or nothing
    supports the state (then the ordinary rules apply, so a start alone is still never negative, Q1). The
    true start is never assumed to lie between the dates, and neither date is preferred."""
    rivals = [s for s in starts if s.rivals]
    if not rivals:
        return None
    support, against, imprecise = [], [], []
    for s in rivals:
        if at < s.lo:
            against.append(s.claims[0])
        elif at < s.hi:
            imprecise.append(s.claims[0])
        elif pos or _joined([s], ends, positive, at):
            support.append(s.claims[0])
    if not support:
        return None
    return sorted(support), sorted(against), sorted(imprecise)


def _window_text(s):
    return f"{s.claims[0]}: start in [{_d(s.lo)}, {_d(s.hi)})"


def _between_competing_ends(ends, at):
    competing = sorted((e for e in ends if e.competing), key=lambda e: e.lo)
    for a, b in zip(competing, competing[1:]):
        if a.hi <= at < b.lo:
            return sorted(set(a.claims) | set(b.claims))
    return []


def _joined(starts, ends, positive, at):
    """A start in one claim and a later end, or positive point or span, in another, with no termination
    between them, inside which `at` lies. Returns (start boundary, target claim ids), the tightest pair."""
    targets = [(e.lo, e.claims) for e in ends]
    targets += [(p, (c.id,)) for c in positive if (p := _point(c)) is not None]
    targets += [(s[0], (c.id,)) for c in positive if (s := _span(c))]
    best = None
    for s in starts:
        if not s.hi <= at:
            continue
        for t, ids in targets:
            if not at < t or set(ids) <= set(s.claims):
                continue
            if any(e.lo >= s.hi and e.hi <= t and not set(e.claims) & set(ids) for e in ends):
                continue  # a termination lies between them
            key = (s.hi, -t.timestamp())
            if best is None or key > best[0]:
                best = (key, s, tuple(sorted(ids)))
    return (best[1], best[2]) if best else None


def contribution(c, at, basis_kind):
    """What a cited claim contributes at `at`: "positive", "negative", "ended" (a termination) or "boundary"."""
    if c.polarity == "negative":
        return "negative"
    if _covers(c, at):
        return "positive"
    if basis_kind in ("termination-continuing", "conflict") and c.valid.to_latest is not None and c.valid.to_latest <= at:
        return "ended"
    return "boundary"


# --- results --------------------------------------------------------------------------------------------

def _result(answer, kind, claim_ids, notes, explanation):
    ids = tuple(sorted(set(claim_ids)))
    text = explanation + ("" if not notes else " Note: " + "; ".join(notes) + ".")
    return Classification(answer, Basis(kind, ids), text, tuple(notes))


def _ids(claims):
    return ", ".join(sorted(c.id for c in claims))


def _d(t):
    return t.date().isoformat() if t not in (LOW, HIGH) else "an unbounded time"
