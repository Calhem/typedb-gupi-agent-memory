"""Evidential standing of an answer: a dimension separate from the temporal answer and from acceptance
(docs/formation/6c-hardening.md).

The three dimensions:
- **Temporal status:** TRUE, FALSE, PRESUMED, UNKNOWN, CONTESTED, NOT_YET_KNOWN (answer semantics v1 or v2).
  This module never changes it.
- **Evidential standing:** how directly the sources behind the deciding claims support it.
- **Acceptance:** who admitted each deciding claim into memory. Admission into memory is not verification.

Standing is computed only from what the claims record (core/0011): the source's commitment, how the
assertion reached the source, and who originated it. There are no confidence scores and no ranking of
sources.
"""

from dataclasses import dataclass

from gupi import typeql
from gupi.temporal import Answer

DECIDED = (Answer.TRUE, Answer.FALSE, Answer.PRESUMED, Answer.CONTESTED)


@dataclass(frozen=True)
class Support:
    claim_id: str
    contribution: str              # what it contributes: positive, negative, ended, boundary
    qualifiers: tuple              # hedged:<commitment>, reported, quoted, forwarded, rumour, unattributed,
                                   # provenance-not-recorded
    originator: str | None         # the asserter, else the observation's author, else None (unknown)
    originator_label: str | None
    source: str | None             # the evidence's source, standing in for an unknown originator
    accepted_by: str | None        # who admitted it into memory (latest acceptance review)


@dataclass(frozen=True)
class Qualification:
    standing: str                  # direct | qualified | unrecorded | n/a
    definitive: bool               # a TRUE or FALSE that direct (or legacy, unrecorded) evidence supports
    qualifiers: tuple
    originators: tuple             # labels of known originators
    independent: int               # distinct originators (an unknown one counts once per source)
    accepted_by: tuple
    supports: tuple
    explanation: str


def qualifiers(view):
    """A claim's evidential qualifiers. A claim with no formation provenance (core/0011) is legacy."""
    if view.commitment is None and view.attribution_mode is None and view.candidate_id is None:
        return ("provenance-not-recorded",)
    out = []
    if view.commitment not in (None, "certain"):
        out.append(f"hedged:{view.commitment}")
    if view.attribution_mode not in (None, "direct"):
        out.append(view.attribution_mode)
    return tuple(out)


def qualify(tx, answer, deciding):
    """The qualification of `answer`, given its deciding claims as (ClaimView, contribution) pairs."""
    deciding = list(deciding)
    if answer not in DECIDED or not deciding:
        return Qualification("n/a", False, (), (), 0, (), (), "Evidential standing: not applicable "
                             "(no claim decides this answer).")
    ids = [c.id for c, _ in deciding]
    asserters = _asserters(tx, ids)
    authors = _authors(tx, sorted({e.observation_id for c, _ in deciding for e in c.evidence}))
    labels = _labels(tx, set(asserters.values()) | set(authors.values()))
    supports = []
    for c, contribution in deciding:
        author = next((authors[e.observation_id] for e in c.evidence if e.observation_id in authors), None)
        originator = asserters.get(c.id) or author
        accepted = [r for r in c.reviews if r.verdict == "accepted"]
        supports.append(Support(c.id, contribution, qualifiers(c), originator, labels.get(originator),
                                c.evidence[0].source_id if c.evidence else None,
                                accepted[-1].decided_by if accepted else None))
    direct = [s for s in supports if not s.qualifiers]
    legacy = [s for s in supports if s.qualifiers == ("provenance-not-recorded",)]
    standing = "direct" if direct else "unrecorded" if len(legacy) == len(supports) else "qualified"
    definitive = answer in (Answer.TRUE, Answer.FALSE) and standing in ("direct", "unrecorded")
    found = tuple(sorted({q for s in supports for q in s.qualifiers}))
    originators = tuple(sorted({s.originator_label for s in supports if s.originator_label}))
    independent = len({s.originator or f"source:{s.source}" for s in supports})
    accepted_by = tuple(sorted({s.accepted_by for s in supports if s.accepted_by}))
    return Qualification(standing, definitive, found, originators, independent, accepted_by, tuple(supports),
                         _explain(answer, standing, definitive, found, originators, independent, accepted_by))


def _explain(answer, standing, definitive, found, originators, independent, accepted_by):
    words = {"direct": "at least one deciding claim was asserted directly and without hedging",
             "qualified": "every deciding claim is hedged, reported, forwarded or rumoured",
             "unrecorded": "the deciding claims predate formation provenance, so their standing is not recorded"}
    text = f"Evidential standing: {standing}; {words[standing]}."
    if found:
        text += f" Qualifiers: {', '.join(found)}."
    if originators:
        text += f" Originated by: {', '.join(originators)}."
    text += f" Independent originators: {independent}."
    if accepted_by:
        text += f" Admitted into memory by {', '.join(accepted_by)}; admission is not verification."
    if answer in (Answer.TRUE, Answer.FALSE) and not definitive:
        text += f" This {answer.name} is not definitive: it rests only on qualified evidence."
    return text


def _asserters(tx, claim_ids):
    from gupi import retrieval
    return retrieval.asserters(tx, claim_ids)


def _authors(tx, observation_ids):
    if not observation_ids:
        return {}
    rows = typeql.rows_for(tx, "match $o isa observation, has gupi-id == $id, has gupi-id $oid; "
                               "authorship (author: $a, authored: $o); $a has gupi-id $aid;",
                           [{"id": i} for i in observation_ids])
    return {r.get("oid").get_string(): r.get("aid").get_string() for r in rows}


def _labels(tx, referent_ids):
    out = {}
    for rid in sorted(i for i in referent_ids if i):
        docs = typeql.documents(tx, 'match $x isa referent, has gupi-id == $id; fetch { "l": $x.label };', {"id": rid})
        if docs and docs[0].get("l"):
            out[rid] = docs[0]["l"]
    return out
