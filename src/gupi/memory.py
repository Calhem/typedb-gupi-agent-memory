"""The GUPI entry point: idempotent ingestion, decisions and provenance-aware retrieval over TypeDB."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from typedb.driver import TransactionType

from gupi import ids, migrations, retrieval, typeql
from gupi.records import VERDICTS, Batch, Claim, proposition_key
from gupi.temporal import Answer
from gupi.typedb.connection import connect, transaction
from gupi.typeql import label


class ConflictError(Exception):
    """Incoming data contradicts what is stored under the same id (e.g. a referent with another type)."""


SEMANTICS = ("v1", "v2")  # answer semantics; v1 is the default until ADR 0009 is accepted


@dataclass
class IngestReport:
    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AnswerResult:
    answer: Answer
    believed: tuple  # (ClaimView, Truth) for each believed claim whose verdict counted
    considered: tuple  # every matching claim about the proposition recorded by then, believed or not
    evaluation: object = None  # v1: gupi.answering.Evaluation; v2: gupi.answering_v2.Classification
    semantics: str = "v1"      # under v2, `believed` pairs each deciding claim with its contribution
    qualification: object = None  # v2: gupi.qualification.Qualification, the evidential standing (separate)


class Memory:
    def __init__(self, driver, database, clock=None, packs=("core", "people"), require_current_schema=True,
                 constraints=None):
        self.driver = driver
        self.database = database
        self.packs = tuple(packs)
        self._constraints = constraints  # conflict rules; default: the packs' constraints.json
        if require_current_schema:
            todo = migrations.pending(driver, database, self.packs)
            if todo:
                raise RuntimeError(f"database {database!r} needs migrating first ({todo[0].id} and {len(todo) - 1} more): "
                                   "use Memory.open or gupi.migrations.migrate")
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._types = None

    @classmethod
    def open(cls, database, packs=("core",), driver=None, create=False, backup_dir=None, clock=None, constraints=None):
        """Connect, optionally create the database, and apply pending migrations for the given packs."""
        driver = driver or connect()
        if not driver.databases.contains(database):
            if not create:
                raise LookupError(f"database {database!r} does not exist (pass create=True)")
            driver.databases.create(database)
        migrations.migrate(driver, database, packs, backup_dir=backup_dir, clock=clock)
        return cls(driver, database, clock, packs, constraints=constraints)

    # --- schema knowledge, for validating labels before they reach query text ---

    def types(self):
        if self._types is None:
            with transaction(self.driver, self.database, TransactionType.READ) as tx:
                def subs(root):
                    return {r.get("t").get_label() for r in typeql.concept_rows(tx, f"match $t sub {root};")}
                self._types = {"referent": subs("referent"), "claim": subs("claim")}
        return self._types

    def _check(self, kind, type_label):
        label(type_label)
        if type_label not in self.types()[kind]:
            raise ValueError(f"{type_label!r} is not a {kind} type in this database's schema")

    # --- ingestion ---

    def ingest(self, batch: Batch) -> IngestReport:
        """Record a batch in one transaction. Re-ingesting the same batch creates nothing new."""
        for r in batch.referents:
            self._check("referent", r.type)
        for c in batch.claims:
            self._check("claim", c.type)
        report = IngestReport()
        with transaction(self.driver, self.database, TransactionType.WRITE) as tx:
            now = self.clock()
            for s in batch.sources:
                self._ingest_source(tx, s, report)
            for c in batch.contexts:
                self._ingest_context(tx, c, report)
            for r in batch.referents:
                self._ingest_referent(tx, r, report)
            for o in batch.observations:
                self._ingest_observation(tx, o, now, report)
            for m in batch.mentions:
                self._ingest_mention(tx, m, report)
            self._before_claims(tx)
            for c in batch.claims:
                self._ingest_claim(tx, c, now, report)
        return report

    def ingest_many(self, batches):
        """Ingest batches one transaction each. If interrupted, rerunning skips what was committed."""
        return [self.ingest(b) for b in batches]

    def _before_claims(self, tx):
        """Test hook: lets tests interrupt an ingestion half-way through a transaction."""

    @staticmethod
    def _type_of(tx, gupi_id):
        rows = typeql.concept_rows(tx, "match $x isa! $t, has gupi-id == $id;", {"id": gupi_id})
        return rows[0].get("t").get_label() if rows else None

    def _ingest_source(self, tx, s, report):
        existing = self._type_of(tx, s.id)
        if existing:
            if existing != "source":
                raise ConflictError(f"{s.id} exists as a {existing}, not a source")
            report.existing.append(s.id)
            return
        attrs = {"gupi-id": s.id, "source-kind": s.kind, "label": s.label, "uri": s.uri}
        _insert(tx, "$s isa source", attrs)
        report.created.append(s.id)

    def _ingest_context(self, tx, c, report):
        existing = self._type_of(tx, c.id)
        if existing:
            if existing != "context":
                raise ConflictError(f"{c.id} exists as a {existing}, not a context")
            report.existing.append(c.id)
            return
        _insert(tx, "$c isa context", {"gupi-id": c.id, "context-kind": c.kind, "label": c.label})
        report.created.append(c.id)

    def _ingest_observation(self, tx, o, now, report):
        if self._type_of(tx, o.id):
            report.existing.append(o.id)
            return
        if self._type_of(tx, o.source_id) != "source":
            raise ValueError(f"observation {o.record_key!r} refers to unknown source {o.source_id!r}")
        if o.context_id is not None and self._type_of(tx, o.context_id) != "context":
            raise ValueError(f"observation {o.record_key!r} refers to unknown context {o.context_id!r}")
        attrs = {"gupi-id": o.id, "record-key": o.record_key, "content": o.content,
                 "content-hash": o.content_hash, "observed-at": o.observed_at, "received-at": now}
        _insert(tx, "$o isa observation", attrs,
                match="$s isa source, has gupi-id == $source_id;", params={"source_id": o.source_id},
                extra="sourcing (source: $s, observed: $o);")
        if o.context_id is not None:
            typeql.run(tx, "match $o isa observation, has gupi-id == $oid; $c isa context, has gupi-id == $cid; "
                           "insert containment (context: $c, member: $o);", {"oid": o.id, "cid": o.context_id})
        if o.author_id is not None:
            if self._type_of(tx, o.author_id) not in self.types()["referent"]:
                raise ValueError(f"observation {o.record_key!r} names unknown author {o.author_id!r}")
            typeql.run(tx, "match $o isa observation, has gupi-id == $oid; $a isa referent, has gupi-id == $aid; "
                           "insert authorship (author: $a, authored: $o);", {"oid": o.id, "aid": o.author_id})
        report.created.append(o.id)

    def _ingest_mention(self, tx, m, report):
        if self._type_of(tx, m.id):
            report.existing.append(m.id)
            return
        docs = typeql.documents(tx, 'match $o isa observation, has gupi-id == $id; fetch { "content": $o.content };',
                                {"id": m.observation_id})
        if not docs:
            raise ValueError(f"mention cites unknown observation {m.observation_id!r}")
        if docs[0]["content"][m.span_start:m.span_end] != m.surface:
            raise ValueError(f"mention {m.surface!r} does not match the observation text at {m.span_start}..{m.span_end}")
        if self._type_of(tx, m.referent_id) not in self.types()["referent"]:
            raise ValueError(f"mention refers to unknown referent {m.referent_id!r}")
        attrs = {"gupi-id": m.id, "surface-text": m.surface, "span-start": m.span_start, "span-end": m.span_end}
        ref_has, ref_params = _has({"confidence": m.confidence, "method": m.method}, "r")
        _insert(tx, "$m isa mention", attrs,
                match="$o isa observation, has gupi-id == $oid; $x isa referent, has gupi-id == $rid;",
                params={"oid": m.observation_id, "rid": m.referent_id, **ref_params},
                extra=f"mentioning (container: $o, mention: $m); reference (mention: $m, referent: $x){ref_has};")
        report.created.append(m.id)

    def _ingest_referent(self, tx, r, report):
        existing = self._type_of(tx, r.id)
        if existing:
            if existing != r.type:
                raise ConflictError(f"{r.id} exists as a {existing}, not a {r.type}")
            report.existing.append(r.id)
            return
        _insert(tx, f"$x isa {label(r.type)}", {"gupi-id": r.id, "label": r.label})
        report.created.append(r.id)

    def _ingest_claim(self, tx, c: Claim, now, report):
        if self._type_of(tx, c.id):
            report.existing.append(c.id)
            return
        params, match, players = {}, [], {}
        for ref in sorted({ref for _, ref in c.players()}):
            ref_type = self._type_of(tx, ref)
            if ref_type is None or ref_type not in self.types()["referent"]:
                raise ValueError(f"claim refers to unknown referent {ref!r}")
            var = f"p{len(players)}"
            players[ref] = var
            params[f"{var}_id"] = ref
            match.append(f"${var} isa! {label(ref_type)}, has gupi-id == ${var}_id;")
        evidence = []
        for i, e in enumerate(sorted(set(c.evidence), key=lambda e: (e.observation_id, e.span_start or 0))):
            if self._type_of(tx, e.observation_id) != "observation":
                raise ValueError(f"claim cites unknown observation {e.observation_id!r}")
            params[f"o{i}_id"] = e.observation_id
            match.append(f"$o{i} isa observation, has gupi-id == $o{i}_id;")
            span = {"span-start": e.span_start, "span-end": e.span_end}
            evidence.append((f"evidence (supported: $c, support: $o{i})", span, f"e{i}"))
        links = ", ".join(f"{label(role)}: ${players[ref]}" for role, ref in c.players())
        vt = c.valid
        attrs = {
            "gupi-id": c.id, "proposition-key": c.proposition_key, "recorded-at": now,
            "valid-from-earliest": vt.from_earliest, "valid-from-latest": vt.from_latest,
            "valid-to-earliest": vt.to_earliest, "valid-to-latest": vt.to_latest,
            "time-precision": c.time_precision, "valid-to-basis": c.valid_to_basis,
            "method": c.method, "confidence": c.confidence, "extraction-basis": c.basis,
            "polarity": "negative" if c.polarity == "negative" else None,
            "valid-from-basis": c.valid_from_basis, "commitment": c.commitment,
            "attribution-mode": c.attribution_mode, "candidate-id": c.candidate_id, **c.values,
        }
        has, has_params = _has(attrs, "a")
        statements = [f"$c isa {label(c.type)} ({links}){has};"]
        if c.asserted_by is not None:
            if self._type_of(tx, c.asserted_by) not in self.types()["referent"]:
                raise ValueError(f"claim names unknown asserter {c.asserted_by!r}")
            match.append("$asserter isa referent, has gupi-id == $asserter_id;")
            params["asserter_id"] = c.asserted_by
            statements.append("assertion (asserter: $asserter, asserted: $c);")
        params.update(has_params)
        for head, span, prefix in evidence:
            span_has, span_params = _has(span, prefix)
            statements.append(f"{head}{span_has};")
            params.update(span_params)
        typeql.run(tx, "match\n" + "\n".join(match) + "\ninsert\n" + "\n".join(statements), params)
        report.created.append(c.id)

    # --- decisions: historical events stamped with GUPI's clock ---

    def review(self, claim_id, verdict, decided_by, reason=None):
        """Record a review. Repeating the claim's latest decision (same verdict and decider) is a no-op."""
        return self.review_many([(claim_id, verdict)], decided_by, reason)[0]

    def review_many(self, decisions, decided_by, reason=None):
        """Record several reviews in one transaction (all or none). `decisions` is [(claim id, verdict)].

        Each review is still its own historical event. A claim may appear only once per batch.
        """
        if not decided_by:
            raise ValueError("every decision needs a decided_by")
        ids_seen = [cid for cid, _ in decisions]
        if len(set(ids_seen)) != len(ids_seen):
            raise ValueError("a claim can be reviewed only once per batch")
        for _, verdict in decisions:
            if verdict not in VERDICTS:
                raise ValueError(f"verdict must be one of {VERDICTS}")
        with transaction(self.driver, self.database, TransactionType.WRITE) as tx:
            now = self.clock()
            return [self._review(tx, now, cid, verdict, decided_by, reason) for cid, verdict in decisions]

    def _review(self, tx, now, claim_id, verdict, decided_by, reason):
        view = retrieval.claim(tx, claim_id)
        if view is None:
            raise KeyError(claim_id)
        if view.reviews:
            latest = view.reviews[-1]
            if latest.verdict == verdict and latest.decided_by == decided_by:
                return latest.id
        self._check_clock(now, [view.recorded_at] + [r.recorded_at for r in view.reviews])
        return self._insert_review(tx, now, claim_id, verdict, decided_by, reason)

    def supersede(self, old_id, new_id, reason=None, decided_by=None):
        """Record that `new_id` replaces `old_id` (a correction). Both claims are kept.

        Superseding a pair whose supersession was withdrawn reinstates it (a new acceptance review on it).
        """
        if old_id == new_id:
            raise ValueError("a claim cannot supersede itself")
        sup_id = ids.stable_id("supersession", old_id, new_id)
        with transaction(self.driver, self.database, TransactionType.WRITE) as tx:
            now = self.clock()
            if self._type_of(tx, sup_id):
                view = next(s for s in retrieval.claim(tx, old_id).supersessions if s.id == sup_id)
                if not view.in_force_at(now):
                    self._check_clock(now, [view.recorded_at] + [r.recorded_at for r in view.reviews])
                    self._insert_review(tx, now, sup_id, "accepted", decided_by or "unspecified", reason, "supersession")
                return sup_id
            views = [retrieval.claim(tx, i) for i in (old_id, new_id)]
            if None in views:
                raise KeyError(old_id if views[0] is None else new_id)
            self._check_clock(now, [v.recorded_at for v in views])
            attrs = {"gupi-id": sup_id, "recorded-at": now, "reason": reason}
            _insert(tx, "$s isa supersession (superseded: $old, replacement: $new)", attrs,
                    match="$old isa claim, has gupi-id == $old_id; $new isa claim, has gupi-id == $new_id;",
                    params={"old_id": old_id, "new_id": new_id})
            return sup_id

    def withdraw_supersession(self, supersession_id, decided_by, reason=None):
        """Undo a correction from now on: the replaced claim's own reviews decide its status again."""
        if not decided_by:
            raise ValueError("every decision needs a decided_by")
        with transaction(self.driver, self.database, TransactionType.WRITE) as tx:
            now = self.clock()
            docs = typeql.documents(tx, 'match $s isa supersession, has gupi-id == $id, links (superseded: $o); '
                                        'fetch { "old": $o.gupi-id };', {"id": supersession_id})
            if not docs:
                raise KeyError(supersession_id)
            view = next(s for s in retrieval.claim(tx, docs[0]["old"]).supersessions if s.id == supersession_id)
            if not view.in_force_at(now):
                return None
            self._check_clock(now, [view.recorded_at] + [r.recorded_at for r in view.reviews])
            return self._insert_review(tx, now, supersession_id, "retracted", decided_by, reason, "supersession")

    def _insert_review(self, tx, now, target_id, verdict, decided_by, reason, target_type="claim"):
        review_id = ids.stable_id("review", target_id, verdict, now, decided_by)
        attrs = {"gupi-id": review_id, "verdict": verdict, "recorded-at": now, "decided-by": decided_by, "reason": reason}
        _insert(tx, "$r isa review (reviewed: $x)", attrs,
                match=f"$x isa {label(target_type)}, has gupi-id == $target_id;", params={"target_id": target_id})
        return review_id

    def suggest_supersessions(self, at=None):
        """Suggest corrections among believed claims about the same thing from the same source, newer replacing
        older by when the source SAID them (observed-at), never by arrival order. Nothing is applied."""
        from gupi import conflicts
        at = at or self.clock()
        found, by_id = self._conflicts_with_views(at, (conflicts.CONTRADICTION, conflicts.DIFFERING))
        out = []
        for x in found:
            a, b = (by_id[i] for i in x.claim_ids)
            if x.kind == conflicts.DIFFERING and a.values != b.values:
                continue  # e.g. two job titles that may be sequential (a promotion): replacing one would lose history
            said = {c.id: max((e.observed_at for e in c.evidence if e.observed_at), default=None) for c in (a, b)}
            sources = {c.id: {e.source_id for e in c.evidence} for c in (a, b)}
            if None in said.values() or said[a.id] == said[b.id] or not (sources[a.id] & sources[b.id]):
                continue
            old, new = sorted((a, b), key=lambda c: said[c.id])
            arrived = "after" if old.recorded_at > new.recorded_at else "before"
            out.append({"old": old.id, "new": new.id, "conflict": x.kind,
                        "reason": f"same source; newer statement ({said[new.id].date()}) than {said[old.id].date()}, "
                                  f"which arrived {arrived} it; {x.reason}"})
        return out

    def mark_alternatives(self, claim_ids, reason=None):
        """Record that these claims are competing readings of the same evidence."""
        claim_ids = sorted(set(claim_ids))
        if len(claim_ids) < 2:
            raise ValueError("alternatives need at least two claims")
        alt_id = ids.stable_id("alternatives", claim_ids)
        with transaction(self.driver, self.database, TransactionType.WRITE) as tx:
            if self._type_of(tx, alt_id):
                return alt_id
            now = self.clock()
            params, match = {}, []
            for i, cid in enumerate(claim_ids):
                if self._type_of(tx, cid) not in self.types()["claim"]:
                    raise KeyError(cid)
                params[f"c{i}_id"] = cid
                match.append(f"$c{i} isa claim, has gupi-id == $c{i}_id;")
            options = ", ".join(f"option: $c{i}" for i in range(len(claim_ids)))
            _insert(tx, f"$a isa alternatives ({options})", {"gupi-id": alt_id, "recorded-at": now, "reason": reason},
                    match=" ".join(match), params=params)
            return alt_id

    @staticmethod
    def _check_clock(now, earlier):
        if any(now < t for t in earlier):
            raise ValueError("the clock is behind already-recorded history; transaction time cannot go backwards")

    # --- retrieval ---

    def claims(self, claim_ids):
        with transaction(self.driver, self.database, TransactionType.READ) as tx:
            return retrieval.claims_by_ids(tx, claim_ids)

    def find_claim(self, prefix):
        """The one claim whose id starts with `prefix` (with or without "claim:"), found by TypeDB."""
        wanted = prefix if ":" in prefix else f"claim:{prefix}"
        with transaction(self.driver, self.database, TransactionType.READ) as tx:
            found = [i for i in retrieval.claim_ids_with_prefix(tx, wanted) if i.startswith(wanted)]
        if len(found) != 1:
            raise LookupError(f"{'no' if not found else 'more than one'} claim matches {prefix!r}")
        return self.claim(found[0])

    def identity_claims(self):
        with transaction(self.driver, self.database, TransactionType.READ) as tx:
            return retrieval.claims_of_type(tx, "identity")

    def claim(self, claim_id):
        with transaction(self.driver, self.database, TransactionType.READ) as tx:
            return retrieval.claim(tx, claim_id)

    def identity_groups(self, at, tx=None):
        """Referents merged by identity claims accepted at `at` (only accepted identities are read)."""
        from gupi import identity

        def read(tx):
            return identity.equivalents(retrieval.claims_by_ids(tx, retrieval.believed_of_type(tx, "identity", at)), at)
        if tx is not None:
            return read(tx)
        with transaction(self.driver, self.database, TransactionType.READ) as tx:
            return read(tx)

    def constraints(self):
        """The domain conflict rules for this memory's packs (constraints.json), or those passed in."""
        from gupi import conflicts
        if self._constraints is None:
            self._constraints = conflicts.load_constraints(self.packs)
        return self._constraints

    def review_queue(self, at=None, claim_type=None, method=None, limit=None):
        """Claims awaiting a decision at `at` (default now), oldest first, with conflicts against believed claims.

        TypeDB selects and limits the hypotheses; each is compared only with the believed claims that could
        conflict with it (same proposition, or the same player under a one-at-a-time rule)."""
        from gupi import conflicts, review
        at = at or self.clock()
        rules = self.constraints()
        kinds = (conflicts.CONTRADICTION, conflicts.DIFFERING)
        with transaction(self.driver, self.database, TransactionType.READ) as tx:
            queued = retrieval.claims_by_ids(tx, retrieval.hypothesis_ids(tx, at, claim_type, method, limit))
            groups = self.identity_groups(at, tx)
            related = {}
            for c in queued:
                related[c.id] = retrieval.claims_by_ids(tx, self._related_believed(tx, c, at, groups, rules))

        def against_believed(c):
            found = conflicts.detect([c] + [x for x in related[c.id] if x.id != c.id], rules, include=kinds, groups=groups)
            return [x for x in found if c.id in x.claim_ids]
        return review.queue(queued, at, against_believed)

    def _related_believed(self, tx, c, at, groups, rules):
        """Ids of believed claims that could conflict with claim c."""
        keys = {proposition_key(c.type, combo) for combo in _expand(dict(c.roles), groups)}
        ids = set(retrieval.believed_among(tx, retrieval.recorded_with_keys(tx, keys, at), at))
        rule = rules["one_player_at_a_time"].get(c.type)
        if rule and rule["per"] in c.roles:
            players = {m for r in c.roles[rule["per"]] for m in groups.get(r, {r})}
            ids |= set(retrieval.believed_with_player(tx, c.type, rule["per"], players, at))
        return ids

    def conflicts(self, at=None, include=None):
        """Relations between the claims believed at `at` (default now): contradictions, differing evidence, ...

        TypeDB finds the groups that can conflict (shared proposition keys, shared players under a
        one-at-a-time rule, merged identities); pairs are compared only inside each group."""
        from gupi import conflicts
        kinds = include or (conflicts.CONTRADICTION, conflicts.DIFFERING)
        return self._conflicts_with_views(at or self.clock(), kinds)[0]

    def _conflicts_with_views(self, at, kinds):
        from gupi import conflicts
        rules = self.constraints()
        with transaction(self.driver, self.database, TransactionType.READ) as tx:
            groups = self.identity_groups(at, tx)
            buckets = [retrieval.believed_among(tx, retrieval.recorded_with_keys(tx, [k], at), at)
                       for k in retrieval.shared_keys_believed(tx, at)]
            for claim_type, rule in rules["one_player_at_a_time"].items():
                for pid in retrieval.shared_players_believed(tx, claim_type, rule["per"], at):
                    buckets.append(set(retrieval.believed_with_player(tx, claim_type, rule["per"], [pid], at)))
            for members in {g for g in groups.values() if len(g) > 1}:
                buckets.append(set(retrieval.believed_involving(tx, members, at)))
            by_id = {c.id: c for c in retrieval.claims_by_ids(tx, set().union(*buckets) if buckets else set())}
        found = {}
        for bucket in buckets:
            for x in conflicts.detect([by_id[i] for i in sorted(bucket)], rules, include=kinds, groups=groups):
                found[(x.kind, x.claim_ids)] = x
        return [found[k] for k in sorted(found)], by_id

    def all_claims(self):
        """Every claim. For small databases, tests and debugging only: retrieval paths never call this."""
        with transaction(self.driver, self.database, TransactionType.READ) as tx:
            return retrieval.all_claims(tx)

    def claims_about(self, referent_id):
        """Every claim involving the referent, with history and evidence, believed or not."""
        with transaction(self.driver, self.database, TransactionType.READ) as tx:
            return retrieval.claims_about(tx, referent_id)

    def believed_ids(self, at):
        """Ids of claims believed at transaction time `at`, computed by TypeDB (`believed_at`)."""
        with transaction(self.driver, self.database, TransactionType.READ) as tx:
            docs = typeql.documents(tx, 'match let $c in believed_at($at); fetch { "id": $c.gupi-id };', {"at": at})
        return {d["id"] for d in docs}

    def ask(self, claim_type, roles, valid_at, believed_at=None, values=None, semantics="v1"):
        """Did `claim_type(roles)` (optionally with these attribute values) hold at `valid_at`, as believed at
        `believed_at` (default: now)? Returns the answer with the claims behind it.

        TypeDB selects the claims about the proposition recorded by `believed_at` and decides which are
        believed. Referents that accepted identity claims say are the same are treated as one.

        `semantics` is "v1" (ADR 0003, 0006, 0007; the default) or "v2" (ADR 0009, proposed).
        """
        from gupi.answering import evaluate
        from gupi.answering_v2 import classify, contribution
        if semantics not in SEMANTICS:
            raise ValueError(f"semantics must be one of {SEMANTICS}")
        self._check("claim", claim_type)
        believed_at = believed_at or self.clock()
        with transaction(self.driver, self.database, TransactionType.READ) as tx:
            groups = self.identity_groups(believed_at, tx)
            keys = {proposition_key(claim_type, combo) for combo in _expand(roles, groups)}
            recorded = retrieval.claims_by_ids(tx, retrieval.recorded_with_keys(tx, keys, believed_at))
            believed_ids = retrieval.believed_among(tx, [c.id for c in recorded], believed_at)
        matching = [c for c in recorded if all(c.values.get(k) == v for k, v in (values or {}).items())]
        bounding = [c for c in recorded if c.id in believed_ids and values and any(k not in c.values for k in values)]
        believed = [c for c in matching if c.id in believed_ids]
        anything = bool(matching or bounding)
        if semantics == "v2":
            r = classify(believed, valid_at, anything, bounding=bounding)
            deciding = tuple((c, contribution(c, valid_at, r.basis.kind)) for c in recorded if c.id in r.basis.claims)
            from gupi.qualification import qualify
            with transaction(self.driver, self.database, TransactionType.READ) as tx:
                q = qualify(tx, r.answer, deciding)
            return AnswerResult(r.answer, deciding, tuple(matching), r, "v2", q)
        positive = [c for c in believed if c.polarity != "negative"]  # v1 cannot express negation
        result = evaluate(positive, valid_at, anything_recorded=anything,
                          bounding=[c for c in bounding if c.polarity != "negative"])
        return AnswerResult(result.answer, result.used, tuple(matching), result)

    def query(self, question):
        """Answer a structured question (gupi.query.Question) with citations, temporal context and exclusions."""
        from gupi import query
        return query.answer(self, question)

    def query_by_name(self, claim_type, roles_by_name, valid_at, believed_at=None, values=None, semantics="v1"):
        """Like query(), with fixed roles given by name; use None for the open role."""
        from gupi import query
        return query.by_name(self, claim_type, roles_by_name, valid_at, believed_at, values, semantics)

    def explore(self, referent_id, depth=2, believed_at=None, valid_at=None, max_nodes=50):
        from gupi import explore
        return explore.explore(self, referent_id, depth, believed_at, valid_at, max_nodes)

    def follow(self, referent_id, steps, valid_at, believed_at=None):
        from gupi import explore
        return explore.follow(self, referent_id, steps, valid_at, believed_at)

    def history(self, referent_id, believed_at=None):
        from gupi import explore
        return explore.history(self, referent_id, believed_at)

    def search(self, text, k=5, believed_at=None):
        """Keyword search over source text received by `believed_at` (the text-only baseline)."""
        from gupi import search
        return search.search(self, text, k, believed_at)

    def suggest_identities(self, record=True):
        """Propose identity claims (as hypotheses, never merged until accepted). Returns the suggestions."""
        from gupi import identity
        found = identity.suggest(self)
        if record and found:
            identity.record(self, found)
        return found


def _expand(roles, groups):
    """Every role assignment obtained by swapping referents for ones accepted as the same."""
    import itertools
    names = sorted(roles)
    options = []
    for role in names:
        refs = (roles[role],) if isinstance(roles[role], str) else tuple(roles[role])
        options.append([tuple(sorted(c)) for c in itertools.product(*[sorted(groups.get(r, {r})) for r in refs])])
    for choice in itertools.product(*options):
        yield {role: (refs[0] if len(refs) == 1 else refs) for role, refs in zip(names, choice)}


def _has(attrs, prefix):
    """`, has label == $prefix_n` clauses and their parameters, skipping None values."""
    clauses, params = [], {}
    for i, (name, value) in enumerate(attrs.items()):
        if value is None:
            continue
        params[f"{prefix}{i}"] = value
        clauses.append(f", has {label(name)} == ${prefix}{i}")
    return "".join(clauses), params


def _insert(tx, head, attrs, match=None, params=None, extra=""):
    has, has_params = _has(attrs, "a")
    body = (f"match {match}\n" if match else "") + f"insert {head}{has}; {extra}"
    typeql.run(tx, body, {**(params or {}), **has_params})
