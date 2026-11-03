"""Formation: validated candidate → formation decision → accepted claim (docs/formation/formation.md).

This is the only module in `gupi.formation` that writes memory. Each candidate gets exactly one recorded
decision:
- **formed:** it becomes a claim, with an acceptance review by the policy, or by the named reviewer who
  approved it
- **withheld:** it stays a candidate
- **review:** it waits for a reviewer's approval
- **rejected:** it is malformed or unsupported

**Acceptance means the assertion was accepted into memory, not that its content is true.** The claim keeps
the source passage, who asserted it and how it reached the source, the source's commitment, its temporal
basis, its polarity and the candidate it came from (core/0011).

Corrections never supersede anything: they produce suggestions for a reviewer (`Memory.supersede` remains
the only way to record one). Candidates themselves are not stored (core/0012 is not approved). The run
report records every decision, so rejected and withheld candidates stay distinguishable from claims.
"""

import json
from dataclasses import dataclass, field

from typedb.driver import TransactionType

from gupi import ids, retrieval, timeexpr, typeql
from gupi.extraction.contract import referent_id
from gupi.formation.candidate import to_dict
from gupi.formation.validate import Unmappable, valid_time, validate
from gupi.memory import _has
from gupi.records import Batch, Claim, Evidence, Mention, Referent
from gupi.typedb.connection import transaction

POLICY = "formation:v1"
OUTCOMES = ("formed", "withheld", "review", "rejected")


@dataclass(frozen=True)
class Decision:
    candidate_id: str
    outcome: str                    # one of OUTCOMES
    reason: str
    decided_by: str | None = None   # who authorised forming: the policy, or the approving reviewer
    claim_id: str | None = None     # set when formed
    suggestion: dict | None = None  # a correction: {"old": claim id or None, "new": claim id, "reason": ...}


@dataclass
class FormationResult:
    run_id: str
    decisions: list = field(default_factory=list)
    already_formed: bool = False    # this exact formation had been run before (nothing new was written)

    def by(self, outcome):
        return [d for d in self.decisions if d.outcome == outcome]

    def counts(self):
        return {o: len(self.by(o)) for o in OUTCOMES}


def decide(candidate, issues, approvals):
    """The formation policy for one candidate. `issues`: its validation issues; `approvals`: {candidate id:
    reviewer} for candidates a reviewer has explicitly authorised. Pure: writes nothing."""
    if issues:
        return Decision(candidate.id, "rejected", "malformed or unsupported: " + "; ".join(i.message for i in issues))
    if candidate.modality != "actual":
        return Decision(candidate.id, "withheld", f"a {candidate.modality} statement: kept as a candidate, "
                                                  "never formed into a claim about what is the case")
    if repeats := [r.target for r in candidate.relations if r.kind == "repeats"]:
        return Decision(candidate.id, "withheld", f"repeats {repeats[0]} (a forwarded or quoted copy): "
                                                  "not an independent attestation")
    try:
        valid_time(candidate)
    except Unmappable as e:
        return Decision(candidate.id, "withheld", f"its time cannot be expressed as a claim's valid time: {e}")
    needs = []
    if candidate.commitment != "certain":
        needs.append(f"hedged by the source ({candidate.commitment})")
    if candidate.attribution.mode == "rumour":
        needs.append("unattributed hearsay")
    if any(r.kind in ("corrects", "retracts") for r in candidate.relations):
        needs.append("a stated correction")
    if needs and candidate.id not in approvals:
        return Decision(candidate.id, "review", "needs a review decision before forming: " + ", ".join(needs))
    if needs:
        return Decision(candidate.id, "formed", "approved by review: " + ", ".join(needs), approvals[candidate.id])
    return Decision(candidate.id, "formed", "an asserted actual condition or event", POLICY)


def form(memory, observation, cset, approvals=None, schema=None, scope=None):
    """Form the candidates of one already-ingested observation. Idempotent: running the same formation again
    writes nothing new and returns the same decisions."""
    approvals = dict(approvals or {})
    run_id = ids.stable_id("run", POLICY, observation.id, to_dict(cset), sorted(approvals.items()))
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        if not typeql.concept_rows(tx, "match $o isa observation, has gupi-id == $id;", {"id": observation.id}):
            raise ValueError(f"observation {observation.id!r} has not been ingested")
        done = bool(typeql.concept_rows(tx, "match $r isa extraction-run, has gupi-id == $id;", {"id": run_id}))
    scope = scope or observation.context_id or observation.id
    issues = {}
    for i in validate(cset, observation, schema):
        issues.setdefault(i.where, []).append(i)
    set_issues = issues.get("set", [])

    result, referents, mentions, claims = FormationResult(run_id, already_formed=done), {}, [], []
    for n, c in enumerate(cset.candidates):
        d = decide(c, set_issues + issues.get(f"candidate {n}", []), approvals)
        if d.outcome == "formed":
            try:
                claim, refs, ms = _claim(c, observation, cset.extractor, scope)
            except ValueError as e:
                d = Decision(c.id, "rejected", f"cannot be formed without inventing anything: {e}")
            else:
                d = Decision(d.candidate_id, d.outcome, d.reason, d.decided_by, claim.id)
                referents.update({r.id: r for r in refs})
                mentions += ms
                claims.append(claim)
        result.decisions.append(d)

    if claims:
        memory.ingest(Batch(referents=tuple(referents.values()), mentions=tuple(dict.fromkeys(mentions)),
                            claims=tuple({c.id: c for c in claims}.values())))
        by_decider = {}
        for d in result.by("formed"):
            by_decider.setdefault(d.decided_by, []).append(d)
        for decider, ds in sorted(by_decider.items()):
            for d in ds:  # one review per claim, each its own historical event; repeating it is a no-op
                memory.review(d.claim_id, "accepted", decider, reason=f"formed from {d.candidate_id}: {d.reason}")
    result.decisions = _suggest_corrections(memory, cset, result.decisions)
    if not done:
        _record_run(memory, run_id, cset, result)
    return result


def _claim(c, obs, method, scope):
    """The claim a candidate becomes. Raises ValueError rather than invent a participant or a date."""
    refs, mentions, roles = [], [], {}
    for p in c.participants:
        if p.surface == "I":
            if not obs.author_id:
                raise ValueError("first person, but the observation has no author")
            rid = obs.author_id
        else:
            rid = referent_id(scope, p.kind, p.surface)
            refs.append(Referent(rid, p.kind, p.surface))
        mentions.append(Mention(obs.id, p.start, p.end, p.surface, rid, None, method))
        roles.setdefault(p.role, []).append(rid)
    asserter = None
    if c.attribution.asserted_by:
        asserter = referent_id(scope, "person", c.attribution.asserted_by)
        refs.append(Referent(asserter, "person", c.attribution.asserted_by))
    vt, to_basis = valid_time(c)
    read = [t for t in c.times if t.earliest is not None or t.latest is not None]
    kinds = {t.kind for t in read}
    from_basis = "stated" if "start" in kinds else "lower-bound" if "holds-since" in kinds else None
    precision = timeexpr.coarsest(*[t.precision for t in read if t.kind != "holds-at"]) if read else None
    claim = Claim(
        c.claim_type, {r: tuple(v) if len(v) > 1 else v[0] for r, v in roles.items()},
        evidence=(Evidence(obs.id, c.passage.start, c.passage.end),), valid=vt, values=dict(c.values),
        time_precision=precision, valid_to_basis=to_basis, method=method, confidence=c.confidence, basis=c.basis,
        polarity=c.polarity, valid_from_basis=from_basis, commitment=c.commitment,
        attribution_mode=c.attribution.mode, asserted_by=asserter, candidate_id=c.id)
    return claim, refs, mentions


def _suggest_corrections(memory, cset, decisions):
    """For each formed candidate with a stated correction: a suggestion naming the claim its target became.
    Nothing is superseded."""
    by_id = {c.id: c for c in cset.candidates}
    targets = {r.target for d in decisions if d.outcome == "formed"
               for r in by_id[d.candidate_id].relations if r.kind in ("corrects", "retracts")}
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        formed_from = retrieval.claim_ids_formed_from(tx, targets)
    out = []
    for d in decisions:
        rel = next((r for r in by_id[d.candidate_id].relations if r.kind in ("corrects", "retracts")), None)
        if d.outcome == "formed" and rel is not None:
            old = formed_from.get(rel.target)
            d = Decision(d.candidate_id, d.outcome, d.reason, d.decided_by, d.claim_id,
                         {"old": old, "new": d.claim_id, "reason": f"{rel.cue or rel.kind}: candidate {d.candidate_id} "
                          f"{rel.kind} {rel.target}" + ("" if old else " (which was never formed into a claim)")})
        out.append(d)
    return out


def _record_run(memory, run_id, cset, result):
    report = {"policy": POLICY, "extractor": cset.extractor, "ir_version": cset.ir_version,
              "decisions": [vars(d) for d in result.decisions], "counts": result.counts()}
    outputs = [d.claim_id for d in result.by("formed")]
    with transaction(memory.driver, memory.database, TransactionType.WRITE) as tx:
        has, params = _has({"gupi-id": run_id, "method": POLICY, "recorded-at": memory.clock(),
                            "run-report": json.dumps(report, sort_keys=True)}, "a")
        typeql.run(tx, f"insert $r isa extraction-run{has};", params)
        for cid in dict.fromkeys(outputs):
            typeql.run(tx, "match $r isa extraction-run, has gupi-id == $rid; $x isa claim, has gupi-id == $cid; "
                           "insert extraction-output (run: $r, output: $x);", {"rid": run_id, "cid": cid})
