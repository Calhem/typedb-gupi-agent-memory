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
import re
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
# gupi.candidate/1.1 claimant kinds -> referent types; anything else (unknown, or not stated) is unclassified
CLAIMANT_REFERENT_KIND = {"person": "person", "organisation": "organization"}
CORRECTION_CUE = re.compile(r"\s*(?:correction|erratum|update to my last|to correct)\b", re.I)
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


def live_schema(memory):
    """The live schema of a Memory's database, read once per Memory object (schema changes need a migration,
    which reopens memory)."""
    cached = getattr(memory, "_formation_schema", None)
    if cached is None:
        from gupi.extraction.contract import SchemaInfo
        with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
            cached = SchemaInfo.load(tx, memory.packs)
        memory._formation_schema = cached
    return cached


def decide(candidate, issues, approvals, rejections=None, copy_of=None):
    """The formation policy for one candidate. Pure: writes nothing.

    - `issues`: its validation issues
    - `approvals` / `rejections`: {candidate id: reviewer} for candidates a reviewer has explicitly authorised
      or refused
    - `copy_of`: an existing claim this candidate is a forwarded or quoted copy of"""
    rejections = rejections or {}
    if candidate.id in rejections:
        return Decision(candidate.id, "rejected", "rejected by review", rejections[candidate.id])
    if issues:
        return Decision(candidate.id, "rejected", "malformed or unsupported: " + "; ".join(i.message for i in issues))
    if candidate.modality != "actual":
        return Decision(candidate.id, "withheld", f"a {candidate.modality} statement: kept as a candidate, "
                                                  "never formed into a claim about what is the case")
    if repeats := [r.target for r in candidate.relations if r.kind == "repeats"]:
        return Decision(candidate.id, "withheld", f"repeats {repeats[0]} (a forwarded or quoted copy): "
                                                  "not an independent attestation")
    if copy_of is not None:
        return Decision(candidate.id, "withheld", f"repeats existing claim {copy_of} (a forwarded or quoted copy): "
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
    if any(r.kind in ("corrects", "retracts", "updates") and r.target is None for r in candidate.relations):
        needs.append("a stated correction whose target is not established")   # D3 (format 1.1)
    elif any(r.kind in ("corrects", "retracts") for r in candidate.relations):
        needs.append("a stated correction")
    elif CORRECTION_CUE.match(candidate.passage.text):
        needs.append("a stated correction whose target could not be identified")  # the passage still says so
    if any(t.kind != "holds-at" and t.earliest is None and t.latest is None for t in candidate.times):
        needs.append("a stated time could not be read")  # forming it would make the claim look timeless
    if needs and candidate.id not in approvals:
        return Decision(candidate.id, "review", "needs a review decision before forming: " + ", ".join(needs))
    if needs:
        return Decision(candidate.id, "formed", "approved by review: " + ", ".join(needs), approvals[candidate.id])
    return Decision(candidate.id, "formed", "an asserted actual condition or event", POLICY)


def form(memory, observation, cset, approvals=None, schema=None, scope=None, rejections=None):
    """Form the candidates of one already-ingested observation. Idempotent: running the same formation again
    writes nothing new and returns the same decisions. `approvals` and `rejections` are reviewers' decisions
    on specific candidates, {candidate id: reviewer}; one candidate cannot be both."""
    approvals, rejections = dict(approvals or {}), dict(rejections or {})
    if both := set(approvals) & set(rejections):
        raise ValueError(f"candidates both approved and rejected: {sorted(both)}")
    run_id = ids.stable_id("run", POLICY, observation.id, to_dict(cset), sorted(approvals.items()),
                           *([sorted(rejections.items())] if rejections else []))
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        if not typeql.concept_rows(tx, "match $o isa observation, has gupi-id == $id;", {"id": observation.id}):
            raise ValueError(f"observation {observation.id!r} has not been ingested")
        done = bool(typeql.concept_rows(tx, "match $r isa extraction-run, has gupi-id == $id;", {"id": run_id}))
        stored = sorted({c.id for c in cset.candidates} & _stored_candidate_ids(tx, [c.id for c in cset.candidates]))
    if stored:
        raise ValueError(f"candidates {stored} are in the candidate store: decide them with gupi.formation.store "
                         "(submit/review), not form(); the two paths are not mixed")
    scope = scope or observation.context_id or observation.id
    issues = {}
    schema = schema or live_schema(memory)  # the same admissibility as schema-aware validation (C1)
    for i in validate(cset, observation, schema):
        issues.setdefault(i.where, []).append(i)
    set_issues = issues.get("set", [])

    drafts = {}
    for c in cset.candidates:  # the claim each candidate would become, to compare it with memory
        try:
            drafts[c.id] = _claim(c, observation, cset.extractor, scope)[0]
        except ValueError:
            pass
    copies = _existing_copies(memory, cset, drafts)

    result, referents, mentions, claims = FormationResult(run_id, already_formed=done), {}, [], []
    for n, c in enumerate(cset.candidates):
        d = decide(c, set_issues + issues.get(f"candidate {n}", []), approvals, rejections, copies.get(c.id))
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
    result.decisions = _suggest_corrections(memory, cset, result.decisions, drafts)
    if not done:
        _record_run(memory, run_id, cset, result)
    return result


def _stored_candidate_ids(tx, candidate_ids):
    """Which of these candidates are in the candidate store (core/0012)."""
    rows = typeql.rows_for(tx, "match $c isa memory-candidate, has gupi-id == $id, has gupi-id $cid;",
                           [{"id": i} for i in candidate_ids]) if candidate_ids else []
    return {r.get("cid").get_string() for r in rows}


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
        # C2: the claimant's referent kind is what the candidate establishes; an absent kind (format 1.0, or 1.1
        # without asserted_by_kind) is not evidence that the claimant is a person
        kind = CLAIMANT_REFERENT_KIND.get(c.attribution.asserted_by_kind, "unclassified")
        asserter = referent_id(scope, kind, c.attribution.asserted_by)
        refs.append(Referent(asserter, kind, c.attribution.asserted_by))
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


def _existing_copies(memory, cset, drafts):
    """{candidate id: claim id} for forwarded or quoted candidates whose statement is already in memory as a
    claim of the same type and polarity, from a passage with the same words, in any conversation. Such a copy
    is not a new attestation. Withholding it merges nothing: no referent is touched."""
    forwarded = [c for c in cset.candidates if c.attribution.mode in ("forwarded", "quoted") and c.id in drafts]
    out = {}
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        for c in forwarded:
            rows = typeql.rows_for(tx, "match $o isa observation, has content $t; $t contains $p; "
                                       "evidence (supported: $c, support: $o); $c isa claim, has gupi-id $cid;",
                                   [{"p": c.passage.text}])
            ids_ = sorted({r.get("cid").get_string() for r in rows} - {drafts[c.id].id})
            same = [x for x in retrieval.claims_by_ids(tx, ids_)
                    if x.type == c.claim_type and x.polarity == c.polarity
                    and x.attribution_mode not in ("forwarded", "quoted")
                    and any(_words(e.quote) == _words(c.passage.text) for e in x.evidence)]
            if same:
                out[c.id] = same[0].id
    return out


def _words(text):
    return " ".join((text or "").casefold().split())


def _suggest_corrections(memory, cset, decisions, drafts):
    """For each candidate that states a correction, formed or awaiting review: a suggestion naming what it may
    correct. A target named by the extractor (an earlier candidate) is used if it became a claim; otherwise
    every believed claim about the same proposition is listed, and more than one is flagged as ambiguous.
    Nothing is superseded."""
    by_id = {c.id: c for c in cset.candidates}
    named = {r.target for c in cset.candidates for r in c.relations
             if r.kind in ("corrects", "retracts", "updates") and r.target is not None}
    keys = {drafts[c.id].proposition_key for c in cset.candidates if c.id in drafts}
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        formed_from = retrieval.claim_ids_formed_from(tx, named)
        recorded = retrieval.recorded_with_keys(tx, keys, memory.clock())
        believed = retrieval.believed_among(tx, recorded, memory.clock())
        views = {v.id: v for v in retrieval.claims_by_ids(tx, believed)}
        named_believed = set(retrieval.believed_among(tx, list(formed_from.values()), memory.clock()))
    out = []
    for d in decisions:
        c = by_id[d.candidate_id]
        rel = next((r for r in c.relations if r.kind in ("corrects", "retracts")
                    or (r.kind == "updates" and r.target is None)), None)
        cued = rel is not None or CORRECTION_CUE.match(c.passage.text)
        if d.outcome not in ("formed", "review") or not cued:
            out.append(d)
            continue
        key = drafts[c.id].proposition_key if c.id in drafts else None
        # D3: every believed claim this could plausibly correct is listed; the extractor's named target is
        # never taken alone when others are plausible, and is not offered at all once it is no longer believed
        plausible = sorted(v.id for v in views.values() if v.proposition_key == key and v.id != d.claim_id)
        named = formed_from.get(rel.target) if rel is not None and rel.target is not None else None
        unestablished = rel is not None and rel.target is None
        note = " (its target is not established by the source: listed for review, never resolved)" if unestablished else ""
        if named and named not in named_believed:
            note = f" (the named target {named} is no longer believed)"
        targets = sorted(set(plausible) | ({named} if named in named_believed else set()))
        cue = rel.cue if rel is not None and rel.cue else "Correction"
        resolution = ("ambiguous" if targets else "missing") if unestablished else \
            ("resolved" if len(targets) == 1 else "ambiguous" if targets else "missing")
        out.append(Decision(d.candidate_id, d.outcome, d.reason, d.decided_by, d.claim_id, {
            "old": targets[0] if resolution == "resolved" else None, "possible_targets": targets,
            "ambiguous": resolution == "ambiguous", "resolution": resolution, "new": d.claim_id,
            "reason": f"{cue}: candidate {d.candidate_id}" + (f" {rel.kind} {rel.target or 'an unestablished target'}" if rel else "")
                      + note + ("" if targets else " (no claim in memory matches its target)")}))
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
