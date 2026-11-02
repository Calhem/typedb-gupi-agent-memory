"""Reading claims back with everything needed to explain them: role players, values, valid time,
decision history and evidence (observation text, span and source)."""

from dataclasses import dataclass, field
from datetime import datetime

from gupi import typeql
from gupi.status import ReviewEvent, Status, status_at
from gupi.temporal import Truth, ValidTime, holds_at

CORE_ATTRIBUTES = {
    "gupi-id", "proposition-key", "recorded-at", "valid-from-earliest", "valid-from-latest",
    "valid-to-earliest", "valid-to-latest", "time-precision", "valid-to-basis", "confidence", "method",
    "occurred-at-earliest", "occurred-at-latest", "extraction-basis",
}


@dataclass(frozen=True)
class EvidenceView:
    observation_id: str
    source_id: str
    content: str
    observed_at: datetime | None
    received_at: datetime | None
    span_start: int | None
    span_end: int | None

    @property
    def quote(self):
        if self.span_start is None or self.span_end is None:
            return self.content
        return self.content[self.span_start:self.span_end]


@dataclass(frozen=True)
class ClaimView:
    id: str
    type: str
    proposition_key: str
    roles: dict[str, tuple[str, ...]]
    values: dict[str, object]
    valid: ValidTime
    recorded_at: datetime
    time_precision: str | None
    valid_to_basis: str | None
    method: str | None
    confidence: float | None
    reviews: tuple[ReviewEvent, ...]
    superseded_by: tuple[tuple[str, datetime], ...]
    supersedes: tuple[str, ...]
    alternatives: tuple[str, ...]
    evidence: tuple[EvidenceView, ...] = field(default=())
    basis: str | None = None

    @property
    def provisional(self):
        """Generic `statement` claims are provisional: typed claims are preferred."""
        return self.type == "statement"

    def status_at(self, t) -> Status:
        return status_at(self.recorded_at, self.reviews, [at for _, at in self.superseded_by], t)

    def holds_at(self, v) -> Truth:
        return holds_at(self.valid, v)


FETCH = """
fetch {
  "type": $t,
  "attrs": { $c.* },
  "players": [ match $c links ($role: $x); $x has gupi-id $xid; fetch { "role": $role, "id": $xid }; ],
  "reviews": [ match $rv isa review, links (reviewed: $c); fetch { $rv.* }; ],
  "superseded_by": [ match $sb isa supersession, links (superseded: $c, replacement: $nb);
                     fetch { "id": $nb.gupi-id, "at": $sb.recorded-at }; ],
  "supersedes": [ match $sp isa supersession, links (replacement: $c, superseded: $ob); fetch { "id": $ob.gupi-id }; ],
  "alternatives": [ match $al isa alternatives, links (option: $c, option: $other); fetch { "id": $other.gupi-id }; ],
  "evidence": [ match $ev isa evidence, links (supported: $c, support: $ob2);
                $sr isa sourcing, links (source: $src, observed: $ob2);
                fetch { "observation": $ob2.gupi-id, "source": $src.gupi-id, "content": $ob2.content,
                        "observed_at": $ob2.observed-at, "received_at": $ob2.received-at,
                        "span_start": $ev.span-start, "span_end": $ev.span-end }; ]
};
"""


def _view(doc):
    a = doc["attrs"]
    t = typeql.parse_datetime
    roles = {}
    for p in doc["players"]:
        role = p["role"]["label"].split(":", 1)[1]
        roles.setdefault(role, set()).add(p["id"])
    reviews = tuple(sorted(
        (ReviewEvent(r["verdict"], t(r["recorded-at"]), r.get("decided-by"), r.get("reason"), r.get("gupi-id"))
         for r in doc["reviews"]),
        key=lambda r: (r.recorded_at, r.id or ""),
    ))
    evidence = tuple(sorted(
        {EvidenceView(e["observation"], e["source"], e["content"], t(e["observed_at"]), t(e["received_at"]),
                      e["span_start"], e["span_end"]) for e in doc["evidence"]},
        key=lambda e: (e.observation_id, e.span_start or 0),
    ))
    return ClaimView(
        id=a["gupi-id"],
        type=doc["type"]["label"],
        proposition_key=a.get("proposition-key"),
        roles={k: tuple(sorted(v)) for k, v in sorted(roles.items())},
        values={k: v for k, v in a.items() if k not in CORE_ATTRIBUTES},
        valid=ValidTime(t(a.get("valid-from-earliest")), t(a.get("valid-from-latest")),
                        t(a.get("valid-to-earliest")), t(a.get("valid-to-latest"))),
        recorded_at=t(a["recorded-at"]),
        time_precision=a.get("time-precision"),
        valid_to_basis=a.get("valid-to-basis"),
        method=a.get("method"),
        confidence=a.get("confidence"),
        reviews=reviews,
        superseded_by=tuple(sorted({(s["id"], t(s["at"])) for s in doc["superseded_by"]}, key=lambda s: s[1])),
        supersedes=tuple(sorted({s["id"] for s in doc["supersedes"]})),
        alternatives=tuple(sorted({o["id"] for o in doc["alternatives"]} - {a["gupi-id"]})),
        evidence=evidence,
        basis=a.get("extraction-basis"),
    )


def _views(docs):
    by_id = {}
    for doc in docs:  # a claim matched through several roles appears more than once
        view = _view(doc)
        by_id[view.id] = view
    return sorted(by_id.values(), key=lambda v: (v.recorded_at, v.id))


def claims_about(tx, referent_id):
    return _views(typeql.documents(
        tx, "match $p has gupi-id == $rid; $c isa! $t, links ($p); $t sub claim;" + FETCH, {"rid": referent_id}))


def claims_for_proposition(tx, proposition_key):
    return _views(typeql.documents(
        tx, "match $c isa! $t, has proposition-key == $key; $t sub claim;" + FETCH, {"key": proposition_key}))


def claim(tx, claim_id):
    found = _views(typeql.documents(
        tx, "match $c isa! $t, has gupi-id == $id; $t sub claim;" + FETCH, {"id": claim_id}))
    return found[0] if found else None


def all_claims(tx):
    return _views(typeql.documents(tx, "match $c isa! $t; $t sub claim;" + FETCH))
