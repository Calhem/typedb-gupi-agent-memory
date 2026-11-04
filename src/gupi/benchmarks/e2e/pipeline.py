"""The GUPI end-to-end path, exactly as production runs it: rules:v2 extraction → validation (inside the
extractor and again in the store) → `store.submit` (candidate persistence + formation:v1 decisions, claims
formed atomically) → optional reviewer decisions through `store.review`. Nothing here decides anything
itself; it only records what the production code did, for tracing."""

import time

from gupi.formation import store
from gupi.formation.rules_v2 import RulesV2
from gupi.formation.validate import Unmappable, valid_time

EXTRACTOR = RulesV2()


def summary(c):
    """A candidate in plain terms (for traces and matching)."""
    return {"id": c.id, "type": c.claim_type, "roles": {p.role: p.surface for p in c.participants},
            "values": dict(c.values), "polarity": c.polarity, "modality": c.modality, "commitment": c.commitment,
            "attribution": c.attribution.mode, "asserted_by": c.attribution.asserted_by,
            "times": [(t.kind, t.phrase, t.earliest and t.earliest.isoformat(), t.latest and t.latest.isoformat())
                      for t in c.times],
            "relations": [r.kind for r in c.relations], "passage": c.passage.text}


def mapped_time(c):
    """The valid time the candidate maps to (gupi.formation.validate.valid_time), or the reason it cannot."""
    try:
        return valid_time(c)[0], None
    except Unmappable as e:
        return None, str(e)


def ingest_extract_submit(memory, clock, obs, batch, prior=(), received=None, timings=None):
    """Ingest one observation (`batch` carries it with its source and context), extract it with rules:v2 and submit its candidates to the store.
    Returns (CandidateSet, extractor Report, SubmitResult or None)."""
    timings = timings if timings is not None else {}
    if received is not None:
        clock.now = received
    t0 = time.perf_counter()
    memory.ingest(batch)
    timings["ingest"] = timings.get("ingest", 0.0) + time.perf_counter() - t0
    t0 = time.perf_counter()
    cset, report = EXTRACTOR.extract(obs, prior=tuple(prior))
    timings["extract"] = timings.get("extract", 0.0) + time.perf_counter() - t0
    result = None
    if cset.candidates:
        t0 = time.perf_counter()
        result = store.submit(memory, obs, cset)
        timings["submit"] = timings.get("submit", 0.0) + time.perf_counter() - t0
    return cset, report, result


def stored_state(memory, candidate_id):
    s = store.get(memory, candidate_id)
    if s is None:
        return {"stored": False}
    return {"stored": True, "status": s.status, "claim": s.claim_id,
            "decisions": [(d.outcome, d.decided_by, d.reason) for d in s.decisions],
            "suggestions": [(x.resolution, list(x.targets)) for x in s.suggestions]}


def outcome_counts(memory, candidate_ids):
    """Latest decision per stored candidate, counted (formed | withheld | review | rejected)."""
    out = {"formed": 0, "withheld": 0, "review": 0, "rejected": 0, "not_stored": 0}
    for cid in sorted(set(candidate_ids)):
        s = store.get(memory, cid)
        out[s.status if s else "not_stored"] += 1
    return out


def first_decisions(memory, candidate_ids):
    """The policy's own decision (the first recorded one) per candidate, counted."""
    out = {"formed": 0, "withheld": 0, "review": 0, "rejected": 0}
    for cid in sorted(set(candidate_ids)):
        s = store.get(memory, cid)
        if s and s.decisions:
            out[s.decisions[0].outcome] += 1
    return out


def believed(memory, claim_id, at):
    return bool(claim_id) and claim_id in set(memory.believed_ids(at))
