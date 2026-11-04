"""Durable memory candidates, append-only formation decisions and correction suggestions (core/0012;
docs/formation/candidate-store.md).

The lifecycle: `submit` stores validated candidates and records the policy's decision on each.
- **"formed":** the claim is created and accepted in the same transaction as the decision.
- **"review":** the candidate waits for `review`.
- **"withheld":** kept, never formed.

`review` appends a reviewer's approval or rejection by candidate id. An approval forms the claim only where
the policy allows it: a plan or hypothetical stays withheld whoever approves it.

**Decisions are append-only.** Each is a new `formation-decision`; the latest is the current status, and
earlier ones are never altered.

**Candidates are not claims.** They are never believed or answered from. Accepting one into memory records
that it was admitted, not that it is true.
"""

import json
from dataclasses import dataclass, replace

from typedb.driver import TransactionType

from gupi import ids, retrieval, typeql
from gupi.formation import form as policy
from gupi.formation.candidate import IR_VERSION, CandidateSet, from_dict, to_dict
from gupi.formation.validate import validate
from gupi.memory import _has
from gupi.records import Batch, Observation
from gupi.typedb.connection import transaction
from gupi.typeql import parse_datetime

VERDICTS = ("approve", "reject")


@dataclass(frozen=True)
class DecisionRecord:
    id: str
    outcome: str                  # formed | withheld | review | rejected
    decided_by: str
    reason: str
    at: object


@dataclass(frozen=True)
class SuggestionRecord:
    id: str
    resolution: str               # resolved | missing | ambiguous
    targets: tuple                # claim ids it may correct; never applied
    reason: str
    at: object


@dataclass(frozen=True)
class StoredCandidate:
    candidate: object             # the gupi.candidate/1 Candidate, exactly as stored
    payload: str                  # its canonical JSON
    observation_id: str
    extractor: str
    ir_version: str
    recorded_at: object
    decisions: tuple              # oldest first; never altered
    claim_id: str | None
    suggestions: tuple

    @property
    def status(self):
        return self.decisions[-1].outcome if self.decisions else None

    def status_at(self, at):
        past = [d for d in self.decisions if d.at <= at]
        return past[-1].outcome if past else None


@dataclass
class SubmitResult:
    stored: list                  # candidate ids now in the store (new or already there)
    invalid: list                 # (candidate index, reason): structurally invalid, not stored
    decisions: list               # DecisionRecords appended by this call


def payload(cset, candidate):
    """The canonical JSON of one candidate with its set's context: what is stored, byte for byte."""
    one = CandidateSet(cset.observation_id, cset.content_hash, cset.extractor, (candidate,), cset.ir_version)
    return json.dumps(to_dict(one), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def submit(memory, observation, cset, schema=None):
    """Store the valid candidates of an ingested observation, each with the policy's decision. Idempotent:
    a candidate already stored is not stored again, and an unchanged decision is not recorded again."""
    issues = {}
    schema = schema or policy.live_schema(memory)  # the same admissibility as schema-aware validation (C1)
    for i in validate(cset, observation, schema):
        issues.setdefault(i.where, []).append(i)
    if issues.get("set"):
        return SubmitResult([], [(None, "; ".join(i.message for i in issues["set"]))], [])
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        legacy = retrieval.claim_ids_formed_from(tx, [c.id for c in cset.candidates])
        stored = policy._stored_candidate_ids(tx, list(legacy))
    if mixed := sorted(set(legacy) - stored):
        raise ValueError(f"candidates {mixed} were already formed by form() (the legacy path), outside the store; "
                         "they are not stored, so the two paths are not mixed")
    result = SubmitResult([], [], [])
    for n, c in enumerate(cset.candidates):
        if f"candidate {n}" in issues:
            result.invalid.append((n, "; ".join(i.message for i in issues[f"candidate {n}"])))
            continue
        d = _apply(memory, observation, cset, c, approvals={}, rejections={}, store=True)
        result.stored.append(c.id)
        if d:
            result.decisions.append(d)
    return result


def review(memory, candidate_id, verdict, reviewer, reason=None):
    """Append a reviewer's decision on a stored candidate. Approving forms its claim only where the policy
    allows; rejecting keeps the candidate, marked rejected. A formed candidate takes no further candidate
    decisions: retracting its claim is a claim review (Memory.review). Repeating the latest decision is a
    no-op."""
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}")
    if not reviewer:
        raise ValueError("a review decision needs a reviewer")
    stored = get(memory, candidate_id)
    if stored is None:
        raise KeyError(candidate_id)
    if stored.status == "formed":
        raise ValueError(f"{candidate_id} was already formed into {stored.claim_id}; review that claim instead")
    obs = _observation(memory, stored.observation_id)
    cset = from_dict(json.loads(stored.payload))
    who = {candidate_id: reviewer}
    return _apply(memory, obs, cset, cset.candidates[0], approvals=who if verdict == "approve" else {},
                  rejections=who if verdict == "reject" else {}, store=False, note=reason)


def get(memory, candidate_id):
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        docs = typeql.documents(tx, "match $c isa memory-candidate, has gupi-id == $id;" + FETCH, {"id": candidate_id})
    return _stored(docs[0]) if docs else None


def pending(memory, at=None):
    """Stored candidates whose latest decision, as of `at` (default: now), is "review"; oldest first."""
    at = at or memory.clock()
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        docs = typeql.documents(tx, "match $c isa memory-candidate, has recorded-at $r; $r <= $at;" + FETCH, {"at": at})
    found = [_stored(d) for d in docs]
    return sorted((s for s in found if s.status_at(at) == "review"), key=lambda s: (s.recorded_at, s.candidate.id))


def suggestions(memory, candidate_id):
    s = get(memory, candidate_id)
    return s.suggestions if s else ()


# --- one decision, atomically with any claim it forms ---------------------------------------------------

def _apply(memory, obs, cset, c, approvals, rejections, store, note=None):
    scope = obs.context_id or obs.id
    try:
        draft, refs, mentions = policy._claim(c, obs, cset.extractor, scope)
    except ValueError:
        draft = refs = mentions = None
    one = replace(cset, candidates=(c,))
    copies = policy._existing_copies(memory, one, {c.id: draft} if draft else {})
    d = policy.decide(c, [], approvals, rejections, copies.get(c.id))
    if d.outcome == "formed" and draft is None:
        d = policy.Decision(c.id, "rejected", "cannot be formed without inventing anything")
    if approvals and d.outcome != "formed":
        d = policy.Decision(c.id, d.outcome, f"approval cannot form it: {d.reason}", approvals[c.id])
    decider = d.decided_by or policy.POLICY
    reason = d.reason + (f" (reviewer's note: {note})" if note else "")
    (sug,) = policy._suggest_corrections(memory, one, [policy.Decision(
        c.id, d.outcome, d.reason, decider, draft.id if d.outcome == "formed" else None)], {c.id: draft} if draft else {})
    with transaction(memory.driver, memory.database, TransactionType.WRITE) as tx:
        now = memory.clock()
        if store and not _exists(tx, c.id):
            _insert_candidate(tx, cset, c, obs, now, draft)
        latest = _latest(tx, c.id)
        if store and latest:
            return None  # already submitted: a policy re-run never adds to, or overrides, recorded decisions
        if latest and (latest["outcome"], latest["by"], latest["reason"]) == (d.outcome, decider, reason):
            return None  # the same decision again: nothing new to record
        if latest and now <= parse_datetime(latest["at"]):
            raise ValueError("a decision must be recorded after the previous one (the clock has not advanced): "
                             "append-only history needs an unambiguous order")
        decision = DecisionRecord(ids.stable_id("decision", c.id, d.outcome, decider, reason, now), d.outcome,
                                  decider, reason, now)
        if d.outcome == "formed":
            memory.ingest_in(tx, Batch(referents=tuple({r.id: r for r in refs}.values()),
                                       mentions=tuple(dict.fromkeys(mentions)), claims=(draft,)), now)
            memory._review(tx, now, draft.id, "accepted", decider, f"formed from {c.id}: {reason}")
            typeql.run(tx, "match $c isa memory-candidate, has gupi-id == $cid; $k isa claim, has gupi-id == $kid; "
                           "insert formed-into (candidate: $c, claim: $k);", {"cid": c.id, "kid": draft.id})
        _insert_decision(tx, c.id, decision)
        if sug.suggestion:
            _insert_suggestion(tx, c.id, sug.suggestion, now)
    return decision


def _exists(tx, candidate_id):
    return bool(typeql.concept_rows(tx, "match $c isa memory-candidate, has gupi-id == $id;", {"id": candidate_id}))


def _insert_candidate(tx, cset, c, obs, now, draft):
    attrs = {"gupi-id": c.id, "ir-version": cset.ir_version, "candidate-payload": payload(cset, c),
             "method": cset.extractor, "recorded-at": now, "proposition-key": draft.proposition_key if draft else None}
    has, params = _has(attrs, "a")
    span, span_params = _has({"span-start": c.passage.start, "span-end": c.passage.end}, "s")
    typeql.run(tx, f"match $o isa observation, has gupi-id == $oid; insert $c isa memory-candidate{has}; "
                   f"$co isa candidate-of (candidate: $c, observation: $o){span};",
               {"oid": obs.id, **params, **span_params})


def _insert_decision(tx, candidate_id, d):
    has, params = _has({"gupi-id": d.id, "formation-outcome": d.outcome, "decided-by": d.decided_by,
                        "reason": d.reason, "recorded-at": d.at}, "a")
    typeql.run(tx, f"match $c isa memory-candidate, has gupi-id == $cid; "
                   f"insert $d isa formation-decision (decided: $c){has};", {"cid": candidate_id, **params})


def _insert_suggestion(tx, candidate_id, s, now):
    targets = sorted(s["possible_targets"])
    sid = ids.stable_id("suggestion", candidate_id, targets)
    if typeql.concept_rows(tx, "match $s isa correction-suggestion, has gupi-id == $id;", {"id": sid}):
        return
    resolution = "resolved" if len(targets) == 1 else "ambiguous" if targets else "missing"
    match = "".join(f" $t{i} isa claim, has gupi-id == $t{i}id;" for i in range(len(targets)))
    links = "".join(f", target: $t{i}" for i in range(len(targets)))
    has, params = _has({"gupi-id": sid, "target-resolution": resolution, "reason": s["reason"], "recorded-at": now}, "a")
    typeql.run(tx, f"match $c isa memory-candidate, has gupi-id == $cid;{match} "
                   f"insert $s isa correction-suggestion (suggested-by: $c{links}){has};",
               {"cid": candidate_id, **params, **{f"t{i}id": t for i, t in enumerate(targets)}})


def _latest(tx, candidate_id):
    docs = typeql.documents(tx, "match $c isa memory-candidate, has gupi-id == $id; "
                                "$d isa formation-decision, links (decided: $c); "
                                'fetch { "id": $d.gupi-id, "outcome": $d.formation-outcome, "by": $d.decided-by, '
                                '"reason": $d.reason, "at": $d.recorded-at };', {"id": candidate_id})
    return max(docs, key=lambda d: (parse_datetime(d["at"]), d["id"])) if docs else None


# --- reading ----------------------------------------------------------------------------------------------

FETCH = """
fetch {
  "attrs": { $c.* },
  "observation": [ match candidate-of (candidate: $c, observation: $o); fetch { "id": $o.gupi-id }; ],
  "decisions": [ match $d isa formation-decision, links (decided: $c); fetch { $d.* }; ],
  "formed": [ match formed-into (candidate: $c, claim: $k); fetch { "id": $k.gupi-id }; ],
  "suggestions": [ match $s isa correction-suggestion, links (suggested-by: $c);
                   fetch { "attrs": { $s.* }, "targets": [ match $s links (target: $t); fetch { "id": $t.gupi-id }; ] }; ]
};
"""


def _stored(doc):
    a = doc["attrs"]
    cset = from_dict(json.loads(a["candidate-payload"]))
    if cset.candidates[0].id != a["gupi-id"]:  # the id is a hash of the content: an altered payload shows
        raise ValueError(f"stored candidate {a['gupi-id']} does not match its payload (it was altered)")
    decisions = sorted((DecisionRecord(d["gupi-id"], d["formation-outcome"], d["decided-by"], d["reason"],
                                       parse_datetime(d["recorded-at"])) for d in doc["decisions"]),
                       key=lambda d: (d.at, d.id))
    sugs = sorted((SuggestionRecord(s["attrs"]["gupi-id"], s["attrs"]["target-resolution"],
                                    tuple(sorted(t["id"] for t in s["targets"])), s["attrs"]["reason"],
                                    parse_datetime(s["attrs"]["recorded-at"])) for s in doc["suggestions"]),
                  key=lambda s: (s.at, s.id))
    formed = sorted(f["id"] for f in doc["formed"])
    return StoredCandidate(cset.candidates[0], a["candidate-payload"], doc["observation"][0]["id"], a["method"],
                           a["ir-version"], parse_datetime(a["recorded-at"]), tuple(decisions),
                           formed[0] if formed else None, tuple(sugs))


def _observation(memory, observation_id):
    """The stored observation, rebuilt exactly (its id must come out the same)."""
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        docs = typeql.documents(tx, "match $o isa observation, has gupi-id == $id; sourcing (source: $s, observed: $o);"
                                    'fetch { "key": $o.record-key, "content": $o.content, "at": $o.observed-at, '
                                    '"source": $s.gupi-id, '
                                    '"ctx": [ match containment (context: $x, member: $o); fetch { "id": $x.gupi-id }; ], '
                                    '"author": [ match authorship (author: $a, authored: $o); fetch { "id": $a.gupi-id }; ] };',
                                {"id": observation_id})
    d = docs[0]
    obs = Observation(d["source"], d["key"], d["content"], parse_datetime(d["at"]),
                      d["ctx"][0]["id"] if d["ctx"] else None, d["author"][0]["id"] if d["author"] else None)
    if obs.id != observation_id:
        raise ValueError(f"observation {observation_id} could not be rebuilt exactly")
    return obs


__all__ = ["IR_VERSION", "submit", "review", "get", "pending", "suggestions", "payload"]
