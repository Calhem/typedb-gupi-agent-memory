"""Structured questions with citations, temporal context and explicit unknowns (docs/adr/0007).

A Question names a claim type, fixed roles (referent ids, or names resolved with `by_name`), at most one
open role ("who?"), optional attribute values, a valid time and a belief time. TypeDB selects the
candidate claims and decides which are believed; gupi.answering turns them into an answer per candidate.
Everything that was looked at and not used is reported with the reason, so an answer can be explained.
"""

import itertools
from dataclasses import dataclass, field
from datetime import datetime

from typedb.driver import TransactionType

from gupi import retrieval, typeql
from gupi.answering import evaluate
from gupi.status import Status
from gupi.temporal import Answer
from gupi.typedb.connection import transaction


@dataclass(frozen=True)
class Question:
    claim_type: str
    roles: dict                      # role -> referent id, or None for the one open role
    valid_at: datetime
    believed_at: datetime | None = None
    values: dict = field(default_factory=dict)
    semantics: str = "v1"            # "v1" (default) or "v2" (docs/adr/0009); recorded in every result


@dataclass(frozen=True)
class Citation:
    claim_id: str
    observation_id: str
    source_id: str
    said_at: datetime | None
    quote: str
    basis: str | None
    verdict: str                     # what this claim says at the valid time: true / false / unknown


@dataclass(frozen=True)
class Binding:
    referents: tuple                 # the open role's referent group (empty for closed questions)
    label: str | None
    answer: Answer
    citations: tuple
    notes: tuple = ()
    basis: object = None             # v2: gupi.answering_v2.Basis (kind and deciding claims)
    explanation: str | None = None   # v2: why this answer, in words


@dataclass
class Result:
    question: Question
    answer: Answer
    bindings: list                   # one per candidate for the open role (one for closed questions)
    excluded: list                   # (claim id, reason): looked at but not used as evidence
    temporal: dict                   # valid time, belief time, and the assumptions used
    steps: list                      # what was retrieved, in order
    ambiguous: list = field(default_factory=list)  # names that matched several unmerged referents

    @property
    def binding(self):
        """Labels of the open role when the answer is TRUE (several if several hold)."""
        if self.answer not in (Answer.TRUE, Answer.PRESUMED):
            return []
        return [b.label for b in self.bindings if b.answer is self.answer and b.label]

    @property
    def citations(self):
        seen, out = set(), []
        for b in self.bindings:
            if self.answer in (Answer.TRUE, Answer.PRESUMED) and b.answer is not self.answer and len(self.bindings) > 1:
                continue
            for c in b.citations:
                if (c.claim_id, c.observation_id) not in seen:
                    seen.add((c.claim_id, c.observation_id))
                    out.append(c)
        return out


# Which per-claim verdicts are cited as evidence for each answer.
SUPPORT = {Answer.TRUE: {"true"}, Answer.FALSE: {"false"}, Answer.CONTESTED: {"true", "false"},
           Answer.UNKNOWN: {"unknown"}, Answer.NOT_YET_KNOWN: set()}


def resolve(tx, name, groups, at):
    """Referent groups whose label is exactly `name` and that GUPI knew about at `at` (mentioned in an
    observation received by then, or created without any mention), with accepted identities merged.
    Referents first mentioned later are invisible to an as-of question."""
    ids = sorted({r.get("id").get_string() for r in typeql.concept_rows(tx, """
        match $x isa referent, has label == $n, has gupi-id $id;
              { reference (mention: $m, referent: $x); mentioning (container: $o, mention: $m);
                $o has received-at $r; $r <= $at; }
              or { not { reference (mention: $m2, referent: $x); }; };""", {"n": name, "at": at})})
    out = []
    for i in ids:
        g = frozenset(groups.get(i, {i}))
        if g not in out:
            out.append(g)
    return out


def _candidates(tx, q, fixed, open_role):
    """Claim ids of q.claim_type with the fixed players (any member of each group), any recording time."""
    t = typeql.label(q.claim_type)
    roles = sorted(fixed)
    body = f"match $c isa {t}, has gupi-id $cid"
    body += "".join(f", links ({typeql.label(r)}: $p{i})" for i, r in enumerate(roles)) + ";"
    body += "".join(f" $p{i} has gupi-id == $r{i};" for i in range(len(roles)))
    if open_role:
        body += f" $c links ({typeql.label(open_role)}: $o); $o has gupi-id $oid;"
    rows = [{f"r{i}": m for i, m in enumerate(combo)} for combo in itertools.product(*[sorted(fixed[r]) for r in roles])]
    found = typeql.rows_for(tx, body, rows) if rows else typeql.concept_rows(tx, body)
    return sorted({r.get("cid").get_string() for r in found})


def _labels(tx, referent_ids):
    ids = sorted(set(referent_ids))
    docs = typeql.documents_for(tx, 'match $x isa referent, has gupi-id == $id; fetch { "id": $x.gupi-id, "label": $x.label };',
                                [{"id": i} for i in ids]) if ids else []
    return {d["id"]: d["label"] for d in docs}


def _why_not(c, t):
    status = c.status_at(t)
    if status is Status.NOT_RECORDED:
        return f"recorded {c.recorded_at.date()}, after the belief time"
    if status is Status.HYPOTHESIS:
        return "an unreviewed hypothesis"
    if status is Status.SUPERSEDED:
        return "superseded by a correction"
    latest = [r for r in c.reviews if r.recorded_at <= t][-1]
    return f"{latest.verdict} by {latest.decided_by} on {latest.recorded_at.date()}" + (f": {latest.reason}" if latest.reason else "")


def _cite(claim, verdict):
    return tuple(Citation(claim.id, e.observation_id, e.source_id, e.observed_at, e.quote, claim.basis, verdict)
                 for e in claim.evidence)


def answer(memory, q: Question):
    """Answer a structured question. See Result for what comes back."""
    memory._check("claim", q.claim_type)
    if q.semantics not in ("v1", "v2"):
        raise ValueError("semantics must be 'v1' or 'v2'")
    t = q.believed_at or memory.clock()
    open_roles = [r for r, v in q.roles.items() if v is None]
    if len(open_roles) > 1:
        raise ValueError("at most one open role per question")
    open_role = open_roles[0] if open_roles else None
    steps = []
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        groups = memory.identity_groups(t, tx)
        fixed = {r: frozenset(groups.get(v, {v})) for r, v in q.roles.items() if v is not None}
        steps.append(f"identity: {sum(1 for g in set(groups.values()) if len(g) > 1)} accepted merge group(s) at {t.date()}")
        ids = _candidates(tx, q, fixed, open_role)
        views = retrieval.claims_by_ids(tx, ids)
        steps.append(f"candidates: {len(views)} {q.claim_type} claim(s) with the given players")
        recorded = [c for c in views if c.recorded_at <= t]
        believed_ids = retrieval.believed_among(tx, [c.id for c in recorded], t)
        steps.append(f"recorded by belief time: {len(recorded)}; believed (TypeDB believed_claim): {len(believed_ids)}")
        open_players = {x for c in views for x in c.roles.get(open_role, ())} if open_role else set()
        labels = _labels(tx, open_players)

    excluded = [(c.id, _why_not(c, t)) for c in views if c.id not in believed_ids]
    if open_role:
        canon = {}
        for p in sorted(open_players):
            canon.setdefault(frozenset(groups.get(p, {p})), set()).add(p)
        candidates = [(g, [c for c in recorded if set(c.roles.get(open_role, ())) & g]) for g in canon]
    else:
        candidates = [(frozenset(), recorded)]

    bindings, notes = [], []
    for group, claims in candidates:
        if q.semantics == "v2":
            binding = _binding_v2(q, group, claims, believed_ids, labels)
            if binding:
                bindings.append(binding)
                notes += binding.notes
            continue
        for c in claims:
            if c.polarity == "negative" and c.id in believed_ids:
                excluded.append((c.id, "an explicit negation, which answer semantics v1 cannot express"))
        claims = [c for c in claims if c.polarity != "negative"]
        matching = [c for c in claims if all(c.values.get(k) == v for k, v in q.values.items())]
        bounding = [c for c in claims if c.id in believed_ids and q.values and any(k not in c.values for k in q.values)]
        if not matching and not bounding:
            continue
        for c in claims:
            if c not in matching and c not in bounding and c.id in believed_ids:
                excluded.append((c.id, "a different " + ", ".join(k for k in q.values if c.values.get(k) not in (None, q.values[k]))))
        ev = evaluate([c for c in matching if c.id in believed_ids], q.valid_at, bool(matching or bounding), bounding)
        support = SUPPORT[ev.answer]
        cites = [x for c, truth in ev.used if truth.value in support for x in _cite(c, truth.value)]
        for s_id, e_id in ev.assembled:
            for c in (x for x in recorded if x.id in (s_id, e_id)):
                cites += _cite(c, c.holds_at(q.valid_at).value)
        for c, reason in ev.ignored:
            excluded.append((c.id, reason))
        label = ", ".join(sorted({labels.get(p) or p for p in group})) if group else None
        bindings.append(Binding(tuple(sorted(group)), label, ev.answer, tuple(dict.fromkeys(cites)), ev.notes))
        notes += ev.notes
    if open_role:
        steps.append(f"open role {open_role!r}: {len(bindings)} candidate(s)")

    overall = _overall(bindings, open_role, anything=bool(recorded))
    temporal = {"valid_at": q.valid_at, "believed_at": t, "semantics": q.semantics, "assumptions": sorted(set(notes)),
                "bounds": {b.label or "answer": [f"{c.claim_id}: {c.verdict}" for c in b.citations] for b in bindings}}
    return Result(q, overall, bindings, excluded, temporal, steps)


def _binding_v2(q, group, claims, believed_ids, labels):
    """One candidate's answer under v2 (docs/adr/0009): the deciding claims are cited with what each contributes."""
    from gupi.answering_v2 import classify, contribution
    matching = [c for c in claims if all(c.values.get(k) == v for k, v in q.values.items())]
    bounding = [c for c in claims if c.id in believed_ids and q.values and any(k not in c.values for k in q.values)]
    if not matching and not bounding:
        return None
    r = classify([c for c in matching if c.id in believed_ids], q.valid_at, True, bounding)
    by_id = {c.id: c for c in claims}
    cites = [x for cid in r.basis.claims if cid in by_id
             for x in _cite(by_id[cid], contribution(by_id[cid], q.valid_at, r.basis.kind))]
    label = ", ".join(sorted({labels.get(p) or p for p in group})) if group else None
    return Binding(tuple(sorted(group)), label, r.answer, tuple(dict.fromkeys(cites)), r.notes, r.basis, r.explanation)


def _overall(bindings, open_role, anything):
    if not bindings:
        return Answer.NOT_YET_KNOWN if not anything else Answer.UNKNOWN
    if not open_role:
        return bindings[0].answer
    answers = [b.answer for b in bindings]
    if Answer.CONTESTED in answers:
        return Answer.CONTESTED
    if Answer.TRUE in answers:
        return Answer.TRUE
    if Answer.PRESUMED in answers:  # v2 only
        return Answer.PRESUMED
    if all(a is Answer.FALSE for a in answers):
        return Answer.FALSE
    if all(a is Answer.NOT_YET_KNOWN for a in answers):
        return Answer.NOT_YET_KNOWN
    return Answer.UNKNOWN


def by_name(memory, claim_type, roles_by_name, valid_at, believed_at=None, values=None, semantics="v1"):
    """Answer a question whose fixed roles are given by name. A name matching several referents that are not
    accepted as the same is reported as ambiguous and answered for each; a name nobody has mentioned gives
    NOT_YET_KNOWN."""
    t = believed_at or memory.clock()
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        groups = memory.identity_groups(t, tx)
        resolved = {r: (resolve(tx, n, groups, t) if n is not None else [None]) for r, n in roles_by_name.items()}
    missing = [roles_by_name[r] for r, gs in resolved.items() if not gs]
    if missing:
        q = Question(claim_type, {}, valid_at, t, values or {}, semantics)
        return Result(q, Answer.NOT_YET_KNOWN, [], [], {"valid_at": valid_at, "believed_at": t, "assumptions": [], "bounds": {}},
                      [f"no referent named {n!r}" for n in missing])
    ambiguous = [roles_by_name[r] for r, gs in resolved.items() if len(gs) > 1]
    results = []
    for combo in itertools.product(*[[(r, g) for g in gs] for r, gs in resolved.items()]):
        roles = {r: (min(g) if g is not None else None) for r, g in combo}
        results.append(answer(memory, Question(claim_type, roles, valid_at, t, values or {}, semantics)))
    if len(results) == 1:
        return results[0]
    first = results[0]
    first.ambiguous = ambiguous
    first.answer = Answer.UNKNOWN
    first.steps.append(f"ambiguous names {ambiguous}: answered separately for {len(results)} referent combinations")
    first.bindings = [b for r in results for b in r.bindings]
    return first
