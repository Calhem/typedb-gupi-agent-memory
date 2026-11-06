"""Reading claims back with everything needed to explain them: role players, values, valid time,
decision history and evidence (observation text, span and source)."""

from dataclasses import dataclass, field
from datetime import datetime

from gupi import typeql
from gupi.status import ReviewEvent, Status, status_at, supersession_in_force
from gupi.temporal import Truth, ValidTime, holds_at

CORE_ATTRIBUTES = {
    "gupi-id", "proposition-key", "recorded-at", "valid-from-earliest", "valid-from-latest",
    "valid-to-earliest", "valid-to-latest", "time-precision", "valid-to-basis", "confidence", "method",
    "occurred-at-earliest", "occurred-at-latest", "extraction-basis", "polarity",
    "valid-from-basis", "commitment", "attribution-mode", "candidate-id",
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
class SupersessionView:
    id: str
    replacement: str
    recorded_at: datetime
    reviews: tuple[ReviewEvent, ...]

    def in_force_at(self, t):
        return supersession_in_force(self.recorded_at, self.reviews, t)


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
    supersessions: tuple[SupersessionView, ...] = field(default=())  # where this claim is the one replaced
    polarity: str = "positive"  # "negative" for an explicit negation (core/0010)
    valid_from_basis: str | None = None   # core/0011, for claims formed from candidates
    commitment: str | None = None
    attribution_mode: str | None = None
    occurred: tuple = (None, None)        # core/0013: when an event happened, [earliest, latest); never a valid time
    candidate_id: str | None = None

    @property
    def provisional(self):
        """Generic `statement` claims are provisional: typed claims are preferred."""
        return self.type == "statement"

    def status_at(self, t) -> Status:
        in_force = [s.recorded_at for s in self.supersessions if s.in_force_at(t)]
        return status_at(self.recorded_at, self.reviews, in_force, t)

    def holds_at(self, v) -> Truth:
        return holds_at(self.valid, v)


FETCH = """
fetch {
  "type": $t,
  "attrs": { $c.* },
  "players": [ match $c links ($role: $x); $x has gupi-id $xid; fetch { "role": $role, "id": $xid }; ],
  "reviews": [ match $rv isa review, links (reviewed: $c); fetch { $rv.* }; ],
  "superseded_by": [ match $sb isa supersession, links (superseded: $c, replacement: $nb);
                     fetch { "id": $nb.gupi-id, "at": $sb.recorded-at, "sid": $sb.gupi-id,
                             "reviews": [ match $sr isa review, links (reviewed: $sb); fetch { $sr.* }; ] }; ],
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
    def review_events(docs):
        return tuple(sorted(
            (ReviewEvent(r["verdict"], t(r["recorded-at"]), r.get("decided-by"), r.get("reason"), r.get("gupi-id"))
             for r in docs),
            key=lambda r: (r.recorded_at, r.id or ""),
        ))
    reviews = review_events(doc["reviews"])
    supersessions = tuple(sorted(
        {s["sid"]: SupersessionView(s["sid"], s["id"], t(s["at"]), review_events(s["reviews"]))
         for s in doc["superseded_by"]}.values(), key=lambda s: (s.recorded_at, s.id)))
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
        occurred=(t(a.get("occurred-at-earliest")), t(a.get("occurred-at-latest"))),
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
        supersessions=supersessions,
        polarity=a.get("polarity", "positive"),
        valid_from_basis=a.get("valid-from-basis"), commitment=a.get("commitment"),
        attribution_mode=a.get("attribution-mode"), candidate_id=a.get("candidate-id"),
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


def claims_of_type(tx, claim_type):
    return _views(typeql.documents(tx, f"match $c isa! $t; $t label {typeql.label(claim_type)};" + FETCH))


# --- server-side filtering (Phase 4): TypeDB selects the candidates; only those are fetched ---

def asserters(tx, claim_ids):
    """{claim id: asserter referent id} for claims with a recorded assertion (core/0011)."""
    ids = sorted(set(claim_ids))
    if not ids:
        return {}
    rows = typeql.rows_for(tx, "match $c isa claim, has gupi-id == $id, has gupi-id $cid; "
                               "assertion (asserter: $a, asserted: $c); $a has gupi-id $aid;", [{"id": i} for i in ids])
    return {r.get("cid").get_string(): r.get("aid").get_string() for r in rows}


def claim_ids_formed_from(tx, candidate_ids):
    """{candidate id: claim id} for claims formed from these candidates (core/0011)."""
    ids = sorted(set(candidate_ids))
    if not ids:
        return {}
    rows = typeql.rows_for(tx, "match $c isa claim, has candidate-id == $k, has gupi-id $cid; $c has candidate-id $kid;",
                           [{"k": k} for k in ids])
    return {r.get("kid").get_string(): r.get("cid").get_string() for r in rows}


def claims_by_ids(tx, claim_ids):
    """Full views for these claims, in one query."""
    ids = sorted(set(claim_ids))
    if not ids:
        return []
    return _views(typeql.documents_for(tx, "match $c isa! $t, has gupi-id == $id; $t sub claim;" + FETCH,
                                       [{"id": i} for i in ids]))


def _ids(rows, var="cid"):
    return sorted({r.get(var).get_string() for r in rows})


def believed_among(tx, claim_ids, at):
    """Which of these claims TypeDB's believed_claim says are believed at `at`."""
    ids = sorted(set(claim_ids))
    if not ids:
        return set()
    return set(_ids(typeql.rows_for(
        tx, "match $c isa claim, has gupi-id == $id, has gupi-id $cid; let $b in believed_claim($c, $at);",
        [{"id": i, "at": at} for i in ids])))


def recorded_with_keys(tx, keys, at):
    """Ids of claims with any of these proposition keys recorded by `at`."""
    keys = sorted(set(keys))
    if not keys:
        return []
    return _ids(typeql.rows_for(
        tx, "match $c isa claim, has proposition-key == $k, has gupi-id $cid, has recorded-at $r; $r <= $at;",
        [{"k": k, "at": at} for k in keys]))


def believed_of_type(tx, claim_type, at):
    return _ids(typeql.concept_rows(
        tx, f"match $c isa {typeql.label(claim_type)}, has gupi-id $cid; let $b in believed_claim($c, $at);", {"at": at}))


def hypothesis_ids(tx, at, claim_type=None, method=None, limit=None):
    """Hypotheses at `at`, oldest first, selected and limited by TypeDB."""
    body = f"match $c isa {typeql.label(claim_type or 'claim')}, has gupi-id $cid, has recorded-at $r; "
    params = {"at": at}
    if method:
        body += "$c has method == $m; "
        params["m"] = method
    body += "let $h in hypothesis_claim($c, $at); sort $r, $cid;"
    if limit:
        body += f" limit {int(limit)};"
    seen, out = set(), []
    for r in typeql.concept_rows(tx, body, params):
        cid = r.get("cid").get_string()
        if cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def believed_involving(tx, referent_ids, at, claim_type="claim"):
    """Believed claims (of a type) in which any of these referents plays a role."""
    ids = sorted(set(referent_ids))
    if not ids:
        return []
    return _ids(typeql.rows_for(
        tx, f"match $p has gupi-id == $rid; $c isa {typeql.label(claim_type)}, links ($p), has gupi-id $cid; "
            "let $b in believed_claim($c, $at);",
        [{"rid": r, "at": at} for r in ids]))


def believed_with_player(tx, claim_type, role, referent_ids, at):
    ids = sorted(set(referent_ids))
    if not ids:
        return []
    return _ids(typeql.rows_for(
        tx, f"match $p has gupi-id == $rid; $c isa {typeql.label(claim_type)}, links ({typeql.label(role)}: $p), "
            "has gupi-id $cid; let $b in believed_claim($c, $at);",
        [{"rid": r, "at": at} for r in ids]))


def shared_keys_believed(tx, at):
    """Proposition keys with two or more claims believed at `at` (TypeDB groups and counts)."""
    rows = typeql.concept_rows(tx, "match $c isa claim, has proposition-key $k; let $b in believed_claim($c, $at); "
                                   "reduce $n = count groupby $k; match $n > 1;", {"at": at})
    return sorted({r.get("k").get_string() for r in rows})


def shared_players_believed(tx, claim_type, role, at):
    """Referents playing `role` in two or more believed claims of `claim_type` (for one-at-a-time rules)."""
    rows = typeql.concept_rows(
        tx, f"match $c isa {typeql.label(claim_type)}, links ({typeql.label(role)}: $p); $p has gupi-id $pid; "
            "let $b in believed_claim($c, $at); reduce $n = count groupby $pid; match $n > 1;", {"at": at})
    return sorted({r.get("pid").get_string() for r in rows})


def claim_ids_with_prefix(tx, prefix):
    return _ids(typeql.concept_rows(tx, "match $c isa claim, has gupi-id $cid; $cid contains $p;", {"p": prefix}))
