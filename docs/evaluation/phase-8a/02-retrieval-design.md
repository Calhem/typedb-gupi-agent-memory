# Phase 8A, part 2: proposed relationship-aware retrieval

**Status: proposal. Nothing here is implemented.** The representative queries below are the exact text run by
[probes/validate_queries.py](probes/validate_queries.py) on TypeDB 3.14.1.

## 1. Design in one paragraph
Keyword search finds seed passages. TypeDB then adds two kinds of neighbours: **structural** (who said it, and what
was said next to it), which exist for every conversation with no extraction, and **claim paths** (one or two hops
through believed claims), which exist where claims were formed. Each result keeps its evidence and qualifications,
and uncertain material is returned labelled, never promoted. The whole thing is bounded, deterministic, and a small
new module beside `gupi.evidence`.

## 2. Data flow
```
question ─► keyword seeds (BM25, top 5)             always available; raw text
        ─► anchors:  referents from the seeds' claims + names in the question (as-of, never merged)
        ─► structural neighbours:  next/previous turn; turns by the named speaker
        ─► claim paths:  1 hop, then 2 hops, believed claims only, shapes bounded, budget capped
        ─► proposition completion:  every claim of each proposition on a path
        ─► qualifications:  commitment, attribution, asserter, pending items, identity candidates
        ─► temporal labels:  existing classify(), per hop, at the other hop's time
        ─► rank, deduplicate, cut to budget ─► EvidenceSet
```

## 3. Responsibilities
| TypeDB | Python |
|---|---|
| select observations by context, word, author, time (existing) | tokenise, BM25, find names in the question |
| belief filtering (`believed_claim`, existing) | classify time and spells (`answering_v2`, existing) |
| bounded path queries from anchors | choose which shapes to run; enforce budgets |
| fetch evidence, reviews, supersessions, asserters (existing `FETCH`) | build path objects; label each hop |
| find pending candidates and suggestions | rank, deduplicate, render |
| type safety of roles and players | nothing: no natural language, fuzzy matching or similarity in TypeQL |

## 4. Interface
Additive. Every existing interface stays.
```python
# gupi/paths.py (new; expected about 300 lines)
Budget(k=10, seeds=5, hops=2, max_paths=50, max_per_anchor=20)
retrieve(memory, question, contexts=None, valid_at=None, believed_at=None, budget=Budget()) -> EvidenceSet
```
| `EvidenceSet` field | Holds |
|---|---|
| `items` | ranked evidence, each with observation, why it is here, and tier |
| `paths` | ordered hops: claim, roles, predicate, evidence quote, qualifiers, temporal label |
| `truncated` | which budget cut anything, so absence is never read as "nothing else exists" |
| `steps` | what ran, as in `Result.steps` |

**Tiers keep uncertainty out of "fact":**
| Tier | Meaning | Source |
|---|---|---|
| `accepted` | believed, certain, direct | claims |
| `qualified` | believed, but reported, hedged, alleged, or standing on a presumed spell | claims + `qualification.qualifiers` |
| `unresolved` | review or withheld candidates, disputes, pending retractions | candidate store; **never a claim** |
| `passage` | raw text with no claim behind it | observations |

## 5. Representative queries
Parameters are passed with `given` (ADR 0004), and only validated labels enter query text.

**Q1. Anchors from seed passages.** Which referents do the claims behind a passage involve?
```typeql
match $o isa observation, has gupi-id == $seed;
      evidence (supported: $c, support: $o);
      $c links ($x); $x isa referent, has gupi-id $xid;
      let $b in believed_claim($c, $t);
select $xid;
```

**Q2. Turns by a named speaker.** Available on all conversations.
```typeql
match $x isa referent, has gupi-id == $rid;
      authorship (author: $x, authored: $o);
      $o has gupi-id $oid;
select $oid;
```

**Q3. A turn's session, in order.** Python picks the neighbours. Ties break on id.
```typeql
match $o isa observation, has gupi-id == $seed;
      containment (context: $c, member: $o);
      containment (context: $c, member: $n);
      $n has gupi-id $nid, has observed-at $at;
sort $at, $nid;
```

**Q4. One hop.** Role-agnostic, believed only, in a fixed order, capped.
```typeql
match $a isa referent, has gupi-id == $rid;
      $c isa claim, links ($a), has gupi-id $cid;
      $c links ($n); not { $n is $a; };
      $n isa referent, has gupi-id $nid;
      let $b in believed_claim($c, $t);
select $cid, $nid;
sort $cid, $nid;
limit 50;
```

**Q5. Two hops.** A pair of claims sharing a middle referent. Nothing here says the two held at the same time.
```typeql
match $a isa referent, has gupi-id == $rid;
      $c1 isa claim, links ($a), has gupi-id $c1id;
      $c1 links ($m); not { $m is $a; };
      $c2 isa claim, links ($m), has gupi-id $c2id;
      not { $c2 is $c1; };
      $c2 links ($z); not { $z is $m; }; not { $z is $a; };
      $m isa referent, has gupi-id $mid; $z isa referent, has gupi-id $zid;
      let $b1 in believed_claim($c1, $t); let $b2 in believed_claim($c2, $t);
select $c1id, $mid, $c2id, $zid;
sort $c1id, $c2id, $zid;
limit 50;
```

**Q6. Proposition completion.** Every claim of a proposition on a path, believed or not, so that spell reasoning
sees a departure or a reinstatement that traversal did not touch. Already in `retrieval.py:231`.
```typeql
match $c isa claim, has proposition-key == $k, has gupi-id $cid, has recorded-at $r;
      $r <= $t;
select $cid;
```

**Q7. Unresolved items near a claim.** Stored candidates in the same conversation still awaiting a decision or
withheld; Python keeps the latest decision per candidate. They are reported, and never treated as claims.
```typeql
match $c isa claim, has gupi-id == $cid;
      evidence (supported: $c, support: $o);
      containment (context: $x, member: $o);
      containment (context: $x, member: $o2);
      candidate-of (candidate: $m, observation: $o2);
      $m has gupi-id $mid;
      formation-decision (decided: $m), has formation-outcome $out, has recorded-at $at;
      $at <= $t;
select $mid, $out, $at;
sort $mid, $at;
```

**Q8. Who supports or disputes a proposition.** All attestations with their evidence and asserter.
```typeql
match $c isa claim, has proposition-key == $k, has gupi-id $cid;
      evidence (supported: $c, support: $o);
      sourcing (source: $s, observed: $o);
      $o has content $text, has observed-at $at;
      $s has gupi-id $sid;
select $cid, $sid, $text, $at;
sort $at, $cid;
```

Full claim views then come from the existing `retrieval.claims_by_ids` (`retrieval.py:208`).

**TypeQL functions:** not needed at first. These queries are short, run per shape, and already reuse
`believed_claim`. A function is a schema change (a migration) and should earn its place: revisit only if the same
pattern appears in three or more places after 8C.

## 6. Identity
- **Names resolve as now:** `query.resolve` (`query.py:91`), as of the belief time. Exact labels only.
- **Several matches stay separate.** Each gets its own paths, reported as ambiguous. Nothing merges.
- **Accepted identities only** expand an anchor (`memory.py:398`). A hypothesis identity is shown as `unresolved`.
- **A first name is not a person.** "Alice" with "Alice Mercer" in the same conversation is only a suggestion
  (`identity.py:100`), so the path is labelled, not followed silently.
- **A speaker's turns are scoped by conversation** (`referent_id` includes the scope), so two same-named people in
  different conversations do not merge. S8 (two in one conversation) remains: abstention stays the safe behaviour.

## 7. Ranking and deduplication
Deterministic, with no learned weights.
1. **Protect keyword recall.** The top 3 keyword hits keep their slots. Dev: without this, simple recall dropped.
2. **Alternate** between the keyword-plus-neighbour list and the structural/path list until the budget is full.
3. **Path evidence** enters as a unit where it fits. A partial path is marked incomplete, not padded.
4. **Deduplicate by observation**, keeping every reason it was found.
5. **Ties** break on tier, score, then id. Every list ends with an id, so runs are repeatable.

A TypeDB `limit` with no `sort` returns an arbitrary subset, so every capped query sorts first (Q4, Q5). This costs
little at this scale (part 5 §2).

## 8. Budgets and hubs
A popular organisation can have hundreds of neighbours. In the probe a third of all people shared one employer.
| Limit | Starting value | Effect when hit |
|---|---|---|
| seeds | 5 | fewer anchors |
| hops | 2 | never more; there is no recursion |
| `max_paths` | 50 per anchor | `truncated` reports it |
| hub rule | a referent with more than 100 claims is not a middle node unless the question names it | stops "everyone at this company" paths |
| result `k` | same as the baseline | identical evidence budget in every comparison |

## 9. Worked example
The Alice scenario was run through real formation on a disposable database:
| Question class | Mechanism | Result expected from the design |
|---|---|---|
| Where did Alice work in 2021? | keyword, then `classify` | the answer, with a year-window caveat |
| Which project through her employer's acquisition? | Q5: employment → acquired → developed | a three-claim path needs **three** hops from Alice, or two from the seed "Northstar" passage; the seed start keeps it bounded |
| Employed there when it was acquired? | per-hop `classify` | PRESUMED across 2022 and UNKNOWN in 2023, depending on which date is right (measured, part 3 §2), never a bare yes |
| How did her relationship with Northstar change? | `history` plus Q8 | ordered periods, no continuity invented |
| Which sources support or dispute the date? | Q8 | both attestations, with sources |
| What is unresolved? | Q7, Q8, `classify` | the date stays UNKNOWN, with both sources shown; the pending retraction is listed |
