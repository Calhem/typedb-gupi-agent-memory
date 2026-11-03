"""Turning the claims about one proposition into an answer at a valid time (docs/adr/0003, 0006, 0007).

Inputs are already filtered by TypeDB: the claims recorded by the belief time, which of them are believed,
and (for value-filtered questions) "bounding" claims about the same relationship without that value.
"""

from dataclasses import dataclass, field

from gupi.temporal import Answer, Truth, combine, false_side, not_ended_by, same_spell, started_by


@dataclass(frozen=True)
class Evaluation:
    answer: Answer
    used: tuple                  # (claim, truth) pairs that counted
    ignored: tuple = ()          # (claim, reason) for believed claims whose verdict did not count
    assembled: tuple = ()        # (start claim id, end claim id) when TRUE was assembled from two claims
    notes: tuple = field(default=())


def evaluate(believed, at, anything_recorded, bounding=()):
    """`believed`: claims believed at the belief time that match the question; `bounding`: believed claims
    about the same relationship that lack a filtered value (they can only say FALSE)."""
    verdicts = [(c, c.holds_at(at)) for c in believed]
    verdicts += [(c, t) for c in bounding if (t := c.holds_at(at)) is Truth.FALSE]
    covering = [x for x, t in verdicts if t is not Truth.FALSE]
    used, ignored = [], []
    for c, t in verdicts:
        if t is Truth.FALSE and covering and not any(same_spell(c.valid, x.valid, false_side(c.valid, at)) for x in covering):
            ignored.append((c, "says FALSE only for a different period than the claims covering this time"))
        else:
            used.append((c, t))
    answer = combine((t for _, t in used), anything_recorded)
    assembled, notes = (), []
    if answer is Answer.UNKNOWN and not any(t is Truth.FALSE for _, t in used):
        starts = [c for c in believed if started_by(c.valid, at)]
        ends = [c for c in believed if not_ended_by(c.valid, at)]
        if starts and ends:
            s, e = starts[0], ends[0]
            answer, assembled = Answer.TRUE, ((s.id, e.id),)
            notes.append("TRUE assembled from a claim that it had started and another that it had not yet ended; "
                         "assumes these describe one continuous period")
    return Evaluation(answer, tuple(used), tuple(ignored), assembled, tuple(notes))
