"""Structural fidelity of generic statements (Phase 7B Stage 4, R1).

A generic statement is stored as roles plus text: subject participant(s), a `predicate-text`, and either an
object participant or `object-text` (or both). Validation checks that every string is grounded; it does not
check that the roles say what the passage says. A statement can be fully grounded and still misleading:

- "X has opened an inquiry into Y", stored as X -has opened-> Y, says X opened Y
- "X is run by the same crew as Y", stored as X -is run by-> Y, says Y runs X

This module checks, from offsets alone (no semantics, no model), whether an object participant is the direct
object of the predicate as it appears in the passage. Anything it cannot verify is reported, and formation sends
the candidate to review instead of forming it. It never repairs a candidate and never refuses one.
"""

import re

# words that may stand between a predicate and its direct object ("accessed the network")
DETERMINERS = frozenset({"", "the", "a", "an"})
POSSESSIVE = re.compile(r"\s*['’]s\b")


def statement_problems(candidate):
    """Reasons this statement's role structure cannot be verified against its passage; [] if it can (or if the
    candidate is not a generic statement)."""
    if candidate.claim_type != "statement":
        return []
    passage, base = candidate.passage.text, candidate.passage.start
    values = dict(candidate.values)
    predicate = (values.get("predicate-text") or "").strip()
    object_text = values.get("object-text")
    problems = []

    spans = []  # where the object text sits in the passage, by any occurrence
    if object_text:
        i = passage.find(object_text)
        while i != -1:
            spans.append((base + i, base + i + len(object_text)))
            i = passage.find(object_text, i + 1)
    for p in candidate.participants:
        if any(lo <= p.start and p.end <= hi for lo, hi in spans):
            problems.append(f"participant {p.surface!r} ({p.role}) lies inside the object text {object_text!r}: "
                            "the roles may not state the passage's relation")

    objects = [p for p in candidate.participants if p.role == "object"]
    if not objects:
        return problems
    ends = [m.end() + base for m in re.finditer(re.escape(predicate), passage, re.I)] if predicate else []
    if not ends:
        problems.append(f"the predicate {predicate!r} does not occur in the passage: its relation to the object "
                        "participant cannot be checked")
        return problems
    for p in objects:
        before = [e for e in ends if e <= p.start]
        gap = candidate.passage.text[before[-1] - base:p.start - base] if before else None
        if gap is None or gap.strip().casefold() not in DETERMINERS:
            between = f"{gap.strip()!r} stands between them" if gap is not None else "it does not follow the predicate"
            problems.append(f"object participant {p.surface!r} is not the direct object of {predicate!r} "
                            f"({between})")
        elif POSSESSIVE.match(passage, p.end - base):
            problems.append(f"object participant {p.surface!r} is a possessor ({p.surface}'s …), not the object of "
                            f"{predicate!r}")
    return problems
