"""What happened to someone, and when (core/0013).

An event is not a state, so `Memory.ask`, which asks whether something held, refuses one. This reads believed events about
a referent, each with its occurrence window, how that date was obtained and when it was said. Sources that give different
dates are reported as disputed and never reconciled: both stay, and no date is preferred.
"""

from dataclasses import dataclass

from typedb.driver import TransactionType

from gupi import retrieval
from gupi.formation.candidate import EVENT_TYPE
from gupi.qualification import qualifiers
from gupi.typedb.connection import transaction


@dataclass(frozen=True)
class Occurrence:
    claim_id: str
    what: str                   # the predicate as written
    about: str | None           # the object as written, if any
    earliest: object            # None: no date was stated
    latest: object              # exclusive
    precision: str | None
    basis: str | None           # stated or derived
    said_at: object             # when the source said it: not when it happened
    qualifiers: tuple
    disputed: bool              # another believed attestation gives a different date


def timeline(memory, referent_id, believed_at=None):
    """Believed events involving this referent or those accepted as the same, dated ones first in order."""
    t = believed_at or memory.clock()
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        group = sorted(memory.identity_groups(t, tx).get(referent_id, {referent_id}))
        found = {c.id: c for r in group for c in retrieval.claims_about(tx, r) if c.type == EVENT_TYPE and c.recorded_at <= t}
        held = retrieval.believed_among(tx, list(found), t)
    views = [c for c in found.values() if c.id in held]
    dates = {}
    for c in views:
        if c.occurred[0] or c.occurred[1]:
            dates.setdefault(_same(c), set()).add(c.occurred)
    out = [Occurrence(c.id, c.values.get("predicate-text"), c.values.get("object-text"), *c.occurred, c.time_precision,
                      c.values.get("occurred-at-basis"), min((e.observed_at for e in c.evidence), default=None),
                      tuple(qualifiers(c)), len(dates.get(_same(c), ())) > 1) for c in views]
    return sorted(out, key=lambda o: (o.earliest is None, o.earliest or o.said_at, o.claim_id))


def _same(c):
    return c.proposition_key, c.values.get("predicate-text"), c.values.get("object-text")
