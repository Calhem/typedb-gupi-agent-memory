"""Run an extractor over observations and record the results as hypotheses.

One extraction run per (extractor, observation). Its id is derived from both, so re-running skips
observations already extracted by the same extractor and prompt version: no repeated LLM calls, no
duplicates. Nothing is ever reviewed here; every extracted claim starts as a hypothesis.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from typedb.driver import TransactionType

from gupi import ids, typeql
from gupi.extraction.contract import SchemaInfo, validate
from gupi.memory import _has
from gupi.records import Batch
from gupi.typedb.connection import transaction


@dataclass(frozen=True)
class ExtractionRequest:
    text: str
    observed_at: datetime | None
    schema: SchemaInfo


class Extractor(Protocol):
    method: str           # recorded on every claim and mention, e.g. "rules:v1"
    model: str | None
    prompt_version: str
    prompt_hash: str

    def extract(self, request: ExtractionRequest) -> dict: ...


@dataclass
class RunResult:
    extracted: list = field(default_factory=list)   # observation ids extracted in this call
    skipped: list = field(default_factory=list)     # already extracted earlier
    claims: list = field(default_factory=list)      # claim ids produced
    rejected: list = field(default_factory=list)    # (observation id, item, reason)
    notes: list = field(default_factory=list)


def run_id(extractor, observation_id):
    return ids.stable_id("run", extractor.method, extractor.prompt_version, extractor.prompt_hash, observation_id)


def extract(memory, extractor, observations, packs=("core", "people")):
    """Extract from already-ingested observations, one transaction per observation."""
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        schema = SchemaInfo.load(tx, packs)
        scopes = _scopes(tx, [o.id for o in observations])
    result = RunResult()
    for obs in observations:
        rid = run_id(extractor, obs.id)
        with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
            done = bool(typeql.concept_rows(tx, "match $r isa extraction-run, has gupi-id == $id;", {"id": rid}))
        if done:
            result.skipped.append(obs.id)
            continue
        raw = extractor.extract(ExtractionRequest(obs.content, obs.observed_at, schema))
        found = validate(raw, obs, schema, scopes.get(obs.id, obs.id), extractor.method)
        if isinstance(raw, dict) and raw.get("problem"):
            found.rejected.append(("output", raw["problem"]))
        memory.ingest(Batch(referents=tuple(found.referents), mentions=tuple(found.mentions),
                            claims=tuple(found.claims)))
        _record_run(memory, extractor, rid, found)
        result.extracted.append(obs.id)
        result.claims += [c.id for c in found.claims]
        result.rejected += [(obs.id, what, why) for what, why in found.rejected]
        result.notes += found.notes
    return result


def _scopes(tx, observation_ids):
    """Referent scope per observation: its context (conversation/document) if it has one, else itself."""
    scopes = {}
    for oid in observation_ids:
        docs = typeql.documents(tx, 'match $o isa observation, has gupi-id == $id; containment (context: $c, member: $o); '
                                    'fetch { "c": $c.gupi-id };', {"id": oid})
        if docs:
            scopes[oid] = docs[0]["c"]
    return scopes


def _record_run(memory, extractor, rid, found):
    outputs = [c.id for c in found.claims] + [m.id for m in found.mentions]
    with transaction(memory.driver, memory.database, TransactionType.WRITE) as tx:
        attrs = {"gupi-id": rid, "method": extractor.method, "model-name": extractor.model,
                 "prompt-version": extractor.prompt_version, "prompt-hash": extractor.prompt_hash,
                 "recorded-at": memory.clock(), "run-report": json.dumps(found.report(), sort_keys=True)}
        has, params = _has(attrs, "a")
        typeql.run(tx, f"insert $r isa extraction-run{has};", params)
        for i, oid in enumerate(outputs):
            typeql.run(tx, "match $r isa extraction-run, has gupi-id == $rid; $x has gupi-id == $oid; "
                           "{ $x isa claim; } or { $x isa mention; }; insert extraction-output (run: $r, output: $x);",
                       {"rid": rid, "oid": oid})


class FixtureExtractor:
    """Returns canned output keyed by observation text. For tests and offline demos only."""

    method = "fixture:v1"
    model = None
    prompt_version = "fixture"
    prompt_hash = "fixture"

    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = 0

    def extract(self, request):
        self.calls += 1
        return self.outputs.get(request.text, {"mentions": [], "claims": []})
