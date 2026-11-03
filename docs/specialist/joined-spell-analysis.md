# Joined spells: analysis against ADR 0007, and a proposed distinction

Date: 2026-11-03. Status: **analysis and proposal; no behaviour changed.** Checked against `main` (`a6d5539`).

## What happens today
ADR 0007 (spell assembly): if believed claims about one proposition include one that certainly started by v
and one that certainly had not ended by v, and none counts as FALSE at v, the answer is **TRUE**, with a note
that it assumes one continuous period. Implemented in `gupi/answering.py` (`evaluate`): `Answer.TRUE`, the
pair in `Evaluation.assembled`, the note in `notes`; `gupi/query.py` cites both claims.

Callers that read only `answer` cannot tell an assembled TRUE from a directly supported one.

Where it is relied on: one frozen benchmark question (Phase 4 `q01`, "joined in January" plus "left in
May", asked about March, gold TRUE), the README example (Marco Rossi), and two tests
(`tests/unit/test_spells.py`, `tests/integration/test_server_filtering.py`). Phase 5 is unaffected
(retrieval only).

## Worked cases (current code, `answering.evaluate`)
Claims are about one proposition, e.g. employment(Alice, Acme). "Truth" is what actually happened in the
scenario.

| Case | Believed claims | Asked | GUPI today | Truth | Verdict |
|---|---|---|---|---|---|
| F | "since 2023, still true on 1 Feb 2025" | Jun 2024 | TRUE (direct) | TRUE | right |
| E | the same claim alone | Mar 2025 | UNKNOWN | unknown | right |
| A | "joined Jan 2024", "left May 2025" | Jul 2024 | TRUE (assembled) | TRUE if continuous | right only under the continuity assumption |
| D | "since 2023, still true on 1 Feb 2025", "stopped in Apr 2025" | Mar 2025 | TRUE (assembled) | TRUE if continuous | as A |
| C′ | "joined Jan 2024", "left May 2025"; she actually left in Mar 2024 and rejoined in Jan 2025, but neither was recorded | Jul 2024 | **TRUE (assembled)** | FALSE | **confidently false**: the gap is invisible |
| B | "joined Jan 2024", "left Mar 2024", "rejoined Jan 2025", "left May 2025" (all recorded) | 15 Feb 2024 | **FALSE** | TRUE | **confidently false** (not assembly: see below) |

**Case B is a separate, pre-existing defect** (ADR 0006/0007 same-spell rule). "Rejoined Jan 2025" says
"not true before Jan 2025". The rule counts that FALSE because "left May 2025", whose start is unstated, still
covers 15 Feb 2024 and could be the same spell as the rejoin. So a FALSE that is only about the second spell
overrides the first spell, which "joined Jan 2024" and "left Mar 2024" bracket. No existing test covers two
fully recorded spells with a stated start of the second.

Both defects have one cause: claims are reasoned about **one at a time**, never grouped into spells.

## Proposed distinction
1. **Directly supported (TRUE / FALSE):** a single believed claim certainly covers v (TRUE), or certainly
   excludes v *for the spell it describes* with no other spell possibly covering v (FALSE).
2. **Presumed continuity (new outcome, PRESUMED):** no single claim covers v, but a start claim S (certainly
   started by v) and an end claim E (certainly not ended by v) can be joined into one spell, with no believed
   start or end of another spell between them. The answer names S, E and the assumption ("no unrecorded
   break between S and E"). It is not TRUE and is scored separately.
3. **Spells first:** order the believed start and end claims of a proposition into candidate spells (a start,
   then the next end). A boundary's FALSE applies only to its own spell. The answer at v is then TRUE if some
   spell directly covers v, PRESUMED if some spell covers v only by joining, FALSE if v lies between a
   recorded end and the next recorded start (or before the first start, after the last end) and no spell can
   cover it, and UNKNOWN otherwise. CONTESTED stays as now, for believed claims about the same spell that
   disagree.

Expected answers under the proposal: F TRUE, E UNKNOWN, A PRESUMED, D PRESUMED, C′ PRESUMED (still wrong
in fact, but no longer presented as directly supported), B **TRUE** (spell Jan-Mar 2024 brackets 15 Feb).

What the proposal does **not** fix: a gap that nothing records (C′) cannot be detected by any reasoning; it
can only be labelled honestly. Linguistic cues ("rejoined", "returned", "came back") are the formation
engine's job: they should produce a start claim, which then splits the spell.

## Not changing history silently
- Introduce an explicit **answer-semantics version**: `v1` = today's behaviour (assembled TRUE; current
  same-spell rule), `v2` = the proposal. Every result records its version.
- Phase 2-5 results stay as committed under v1. The Phase 4 benchmark keeps v1 for reproducibility; under v2
  its `q01` would become PRESUMED, so a v2 re-run would be reported separately, with the frozen gold unchanged
  and the difference explained.
- `Answer.PRESUMED` is added only under v2, so code written for v1 is not surprised.
- ADR 0007 gets an amendment (or ADR 0009 supersedes its spell section) once approved; the README example is
  updated to say "presumed".
- M1 evaluates under v2 and scores PRESUMED explicitly. Proposed credit: full credit when gold is "true under
  continuity", and counted as an unsupported confident answer when gold is FALSE.

## Decision needed
Approve v2 (distinct PRESUMED outcome, spells first), the versioning approach, and adding the case B
regression test as a known failure (`xfail`) until v2 is implemented.
