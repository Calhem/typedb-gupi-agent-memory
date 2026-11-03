"""Typed records that callers hand to GUPI. Ids are derived from content (see gupi.ids).

Transaction times (recorded-at, received-at) are never taken from callers: GUPI sets them from its clock
when it records something, so the history of what was believed when cannot be rewritten.
"""

from dataclasses import dataclass, field
from datetime import datetime

from gupi import ids
from gupi.temporal import ValidTime
from gupi.typeql import label

VERDICTS = ("accepted", "rejected", "retracted")


def expand_roles(roles):
    """(role, referent id) pairs, sorted, with multi-player roles expanded."""
    pairs = []
    for role, ref in roles.items():
        for r in (ref,) if isinstance(ref, str) else ref:
            pairs.append((label(role), r))
    return sorted(pairs)


def proposition_key(claim_type, roles):
    """What a claim is about (type + role players), independent of what it says or who said it."""
    return ids.stable_id("prop", label(claim_type), expand_roles(roles))


@dataclass(frozen=True)
class Source:
    id: str
    kind: str
    label: str | None = None
    uri: str | None = None


@dataclass(frozen=True)
class Context:
    """A conversation, document or session that groups observations."""

    id: str
    kind: str
    label: str | None = None


@dataclass(frozen=True)
class Observation:
    """Something a source said, verbatim. `record_key` is the source's own id or offset for it.

    `context_id` (optional) places it in a conversation or document, and `author_id` (optional) names the
    referent who said it; neither is part of the id.
    """

    source_id: str
    record_key: str
    content: str
    observed_at: datetime | None = None
    context_id: str | None = None
    author_id: str | None = None

    @property
    def content_hash(self):
        return ids.content_hash(self.content)

    @property
    def id(self):
        return ids.stable_id("obs", self.source_id, self.record_key, self.content_hash)


@dataclass(frozen=True)
class Referent:
    """A thing memory is about. Ids are chosen by the caller (source-scoped); identity resolution is Phase 3."""

    id: str
    type: str
    label: str | None = None

    def __post_init__(self):
        label(self.type)


@dataclass(frozen=True)
class Mention:
    """A span of an observation that names a referent. The surface text must match the span exactly."""

    observation_id: str
    span_start: int
    span_end: int
    surface: str
    referent_id: str
    confidence: float | None = None
    method: str | None = None

    @property
    def id(self):
        return ids.stable_id("mention", self.observation_id, self.span_start, self.span_end, self.referent_id, self.method)


@dataclass(frozen=True)
class Evidence:
    observation_id: str
    span_start: int | None = None
    span_end: int | None = None


@dataclass(frozen=True)
class Claim:
    """One attestation of a typed proposition, e.g. type "reporting", roles {"report": "p:alice", "manager": "p:bob"}.

    `values` holds attributes the claim type owns (e.g. {"job-title": "CTO"}).
    """

    type: str
    roles: dict[str, str | tuple[str, ...]]
    evidence: tuple[Evidence, ...]
    valid: ValidTime = field(default_factory=ValidTime)
    values: dict[str, str | int | float | bool | datetime] = field(default_factory=dict)
    time_precision: str | None = None
    valid_to_basis: str | None = None
    method: str | None = None
    confidence: float | None = None
    basis: str | None = None  # "explicit" or "inferred", for extracted claims

    def __post_init__(self):
        label(self.type)
        if self.basis not in (None, "explicit", "inferred"):
            raise ValueError("basis must be 'explicit' or 'inferred'")
        for name in list(self.roles) + list(self.values):
            label(name)
        if not self.evidence:
            raise ValueError("a claim needs at least one piece of evidence")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def players(self):
        return expand_roles(self.roles)

    @property
    def proposition_key(self):
        return proposition_key(self.type, self.roles)

    @property
    def id(self):
        vt = self.valid
        return ids.stable_id(
            "claim", self.type, self.players(), self.values,
            [vt.from_earliest, vt.from_latest, vt.to_earliest, vt.to_latest],
            self.time_precision, self.valid_to_basis,
            sorted((e.observation_id, e.span_start, e.span_end) for e in self.evidence),
            self.method,
            *([self.basis] if self.basis else []),  # only when set, so Phase 1 ids are unchanged
        )


@dataclass(frozen=True)
class Batch:
    """What one ingestion call records, in one transaction: all of it or none of it."""

    sources: tuple[Source, ...] = ()
    observations: tuple[Observation, ...] = ()
    referents: tuple[Referent, ...] = ()
    claims: tuple[Claim, ...] = ()
    contexts: tuple[Context, ...] = ()
    mentions: tuple[Mention, ...] = ()
