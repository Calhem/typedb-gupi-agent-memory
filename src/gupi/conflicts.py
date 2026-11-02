"""Conflict detection between claims (docs/adr/0006). Detects and explains; never resolves.

Pairs of claims about the same proposition are classified as:
- contradiction: they cannot both be true. One is certainly true at a moment the other says is certainly
  false while their possible periods overlap, or a single-valued attribute (domain constraint) has two
  values that are both certainly true at the same moment.
- differing-evidence: compatible but different in detail (bounds, precision, values that may be
  sequential, e.g. a promotion).
- corroboration: same bounds and values from different evidence.
- separate-periods: their possible periods do not overlap (e.g. two spells of employment).

Domain constraints (a pack's constraints.json) add contradictions across propositions, e.g. a person
certainly reporting to two different managers at the same moment.
"""

import json
from dataclasses import dataclass

from gupi import migrations
from gupi.temporal import certain_period, certainly_false_periods, overlap, possible_period

CONTRADICTION = "contradiction"
DIFFERING = "differing-evidence"
CORROBORATION = "corroboration"
SEPARATE = "separate-periods"


@dataclass(frozen=True)
class Conflict:
    kind: str
    claim_ids: tuple
    reason: str
    period: tuple | None = None  # where the contradiction is certain, if any


def load_constraints(packs):
    rules = {"single_valued_attributes": {}, "one_player_at_a_time": {}}
    for pack in packs:
        path = migrations.BUILTIN / pack / "constraints.json"
        if path.exists():
            data = json.loads(path.read_text())
            for key in rules:
                rules[key].update(data.get(key, {}))
    return rules


def _fmt(period):
    start, end = period
    return f"{start.date() if start else '...'} to {end.date() if end else '...'}"


def opposition(a, b):
    """A period where one claim is certainly true and the other certainly false, or None."""
    for x, y in ((a, b), (b, a)):
        certain = certain_period(x.valid)
        for false in certainly_false_periods(y.valid):
            if (o := overlap(certain, false)) is not None:
                return o
    return None


def compare(a, b, constraints):
    """Classify two claims about the same proposition."""
    ids = tuple(sorted((a.id, b.id)))
    if overlap(possible_period(a.valid), possible_period(b.valid)) is None:
        return Conflict(SEPARATE, ids, "their possible periods do not overlap")
    if (o := opposition(a, b)) is not None:
        return Conflict(CONTRADICTION, ids, f"one says it held and the other says it did not, {_fmt(o)}", o)
    single = set(constraints["single_valued_attributes"].get(a.type, ()))
    differing_values = {k for k in set(a.values) | set(b.values) if a.values.get(k) != b.values.get(k)}
    for attr in sorted(differing_values & single):
        both = overlap(certain_period(a.valid), certain_period(b.valid))
        if both is not None and attr in a.values and attr in b.values:
            return Conflict(CONTRADICTION, ids, f"{attr} is both {a.values[attr]!r} and {b.values[attr]!r}, {_fmt(both)}", both)
    if differing_values:
        return Conflict(DIFFERING, ids, "different " + ", ".join(sorted(differing_values))
                        + " (not certainly at the same time, so possibly sequential)")
    if a.valid == b.valid:
        return Conflict(CORROBORATION, ids, "same proposition, bounds and values from different evidence")
    return Conflict(DIFFERING, ids, "compatible, but with different time bounds or precision")


def detect(claims, constraints, include=(CONTRADICTION, DIFFERING, CORROBORATION, SEPARATE)):
    """All pairwise relations among `claims` (normally those believed at one time), filtered by kind."""
    claims = [c for c in claims if c.type != "identity"]
    found = []
    for i, a in enumerate(claims):
        for b in claims[i + 1:]:
            if a.id == b.id:
                continue
            if a.proposition_key == b.proposition_key:
                found.append(compare(a, b, constraints))
            elif (rule := constraints["one_player_at_a_time"].get(a.type)) and a.type == b.type:
                per, single = rule["per"], rule["single"]
                if a.roles.get(per) == b.roles.get(per) and a.roles.get(single) != b.roles.get(single):
                    both = overlap(certain_period(a.valid), certain_period(b.valid))
                    if both is not None:
                        found.append(Conflict(CONTRADICTION, tuple(sorted((a.id, b.id))),
                                              f"two different {single}s at the same time, {_fmt(both)}", both))
    return [c for c in found if c.kind in include]
