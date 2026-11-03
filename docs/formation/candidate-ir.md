# Memory candidates: intermediate representation `gupi.candidate/1`

Date: 2026-11-03. Status: **Phase 6A, provisional.**
- **Code:** `gupi.formation.candidate` and `gupi.formation.validate`.
- **Tests:** `tests/unit/test_formation_candidate.py`.
- **Not yet used:** no extractor produces this representation yet, and nothing ingests it.

## 1. Purpose
A candidate is what an extractor proposes that one passage of one observation says. It sits between
extractor output and memory, and keeps what today's claims lose (audit.md A1-A5, A7).
- **It is not memory.** It is never believed, reviewed or answered from.
- **It becomes a claim only through a later, explicit formation step** (milestones 6B-6C, plan-6b-6d.md).
- **The `gupi.formation` package imports nothing that can write memory.** A test checks this.

## 2. Structure
A **CandidateSet** holds everything one extractor proposed for one observation:
- `ir_version`
- `observation_id`, and the observation's `content_hash`
- `extractor` (its method, e.g. `rules:v2`)
- the `candidates`

A **Candidate** has these fields:

| Field | Holds |
|---|---|
| `claim_type` | the proposed claim type, a schema label |
| `passage` | observation id, offsets, and the exact text (it must equal the observation's content there) |
| `participants` | each role player **as written**: role, surface text, offsets, referent kind. Resolution to a referent comes later (Phase 3 identity rules). |
| `values` | attribute and text pairs (e.g. `job-title`, `CTO`) |
| `times` | one **TimeEvidence** per time phrase (§3) |
| `polarity` | `positive` or `negative` (an explicit negation; core/0010) |
| `modality` | `actual`, `planned`, `required`, `permitted`, `requested`, `conditional`, `hypothetical` or `question` |
| `commitment` | the **source's** commitment: `certain`, `probable`, `possible` or `unknown` |
| `attribution` | `asserted_by`; `mode` (`direct`, `reported`, `quoted`, `forwarded`, `rumour` or `unattributed`); `via` (intermediaries, nearest first); `transmission` (`forwarded`, `transcribed`, `paraphrased`, `excerpted`, `authenticity-unclear`) |
| `relations` | `corrects`, `retracts`, `updates`, `repeats`, `resumes` or `contradicts`, each to another candidate in the set or to an existing claim (`claim:...`), marked `stated` (with its cue, e.g. "Correction:") or `inferred` |
| `basis` | `explicit` or `inferred` |
| `confidence` | the **extractor's** confidence in its own reading, kept apart from the source's commitment |

**Ids.**
- A candidate's id is a hash of its version and all of its fields, so the same proposal always has the same
  id.
- Relations are part of the id, so relations cannot form cycles.
- **Serialisation:** `to_dict` and `from_dict` give a JSON-ready form that round-trips exactly, ids
  included.

## 3. Time evidence
Each phrase keeps its verbatim text, offsets, the window `gupi.timeexpr` read, precision, whether the
date was explicit or inferred, and any assumption. Its **kind** says what the phrase asserts:

| Kind | Example | Meaning |
|---|---|---|
| `start` | "joined Halden in March 2025" | the state **began** inside the window |
| `end` | "left Halden in May 2025" | the state **ended** inside the window |
| `holds-since` | "has worked here **since** March 2025"; "**Since** March 2025, Nora works at Halden" | the state held from the window, or earlier, until the statement's time. This is **lower-bound evidence of continuity**: it does not say when the state began. |
| `holds-at` | "works at Halden" (at the observation); "was CTO in March 2025" | the state held at some instant in the window |

**"Started in March" against "has worked here since March"** (the owner's requirement; audit.md A1):
- They are different kinds, `start` and `holds-since`.
- The validator rejects a `start` whose phrase follows "since" (code `since-as-start`).
- The mapping (§5) never turns `holds-since` into a start date.

## 4. Structural validation (`validate`)
Validation returns every issue found, as `(where, code, message)`. It never repairs anything. An empty
list means the set is structurally sound, which says nothing about whether it is true.

**What is checked:**
- **The set:** the version; that the observation id and content hash match the observation; that an
  extractor is named; that there are no duplicate candidates.
- **Exact text:** the passage, each participant and each time phrase must equal the observation's text at
  their offsets. Participants and phrases must lie inside the passage.
- **Values:** labels for the claim type, roles and attributes; at least one participant; every enumerated
  value; confidence between 0 and 1.
- **Time:**
  - at most one `start`, one `end` and one `holds-since`
  - every phrase has a window, the right way round, unless it is unread (§6)
  - the start is not entirely after the end
  - no `since-as-start`
- **Relations:** each target is a candidate (in this set, or an earlier one; §6) or a claim id.
- **Against the schema, if given** (`SchemaInfo`, as the extraction contract uses):
  - the claim type exists and is not `identity`
  - each role exists, and the participant's kind may play it
  - each attribute is owned

## 5. Mapping onto a claim's valid time (`valid_time`, provisional)
This is the rule a later formation step will use. It is defined and tested now, but **no code uses it in
6A**.

| Time evidence | Valid time |
|---|---|
| `start` [e, l) | from-earliest e, from-latest l |
| `holds-since` [e, l) | from-latest l **only**, or the statement's own instant if that is earlier ("since June", said on 10 June): certainly held from then; from-earliest stays open |
| `start` and `holds-since` | the start's window, narrowed to the earlier of the two latest bounds |
| `end` [e, l) | to-earliest e, to-latest l; basis `stated` |
| `holds-at` an instant o, no `end` | to-earliest o; basis `ongoing-at-observation` |
| `holds-at` over a coarser window | **not expressible** (raises `Unmappable`). Keep it as a candidate, or as an explicit "held at some time in" claim in a later milestone. |

**What answer semantics v2 then does,** with no change to v2 itself:
- **Inside the open start window,** a `holds-since` claim gives UNKNOWN. It does not give FALSE, and it does
  not compete as a start date.
- **From l to the statement's time,** it gives TRUE.

**The q01 pattern** (January start, "since March", May departure; asked about 15 March):
- with the old start reading, v2 gives **UNKNOWN**: competing starts, Q9
- with the `holds-since` reading, v2 gives **PRESUMED**: January to May, consistent with "since March"

A test checks this. The frozen Phase 4 benchmark is unchanged.

## 6. Clarifications in Phase 6B (same version: no field or meaning changed)
- **Relation targets** may name a candidate from **another** set (an earlier observation in the same thread),
  as well as a candidate in this set or a claim. A set cannot check that such a target exists, so the
  formation step (6C) must.
- **An unread time phrase** (e.g. "last spring") may be kept with no window, provided its precision is
  `unknown`. Its wording is preserved, and it adds no bound to the valid time.

## 7. Versioning
- `gupi.candidate/1` is this document.
- Any change to the fields or their meanings is a new version. The validator accepts only its own version.
- Stored candidates (6B) carry their version, so old ones can be read or migrated deliberately.
