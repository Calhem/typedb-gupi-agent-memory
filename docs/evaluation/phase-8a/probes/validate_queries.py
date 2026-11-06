"""Runs every ```typeql block of 02-retrieval-design.md, as written, on a disposable gupi-probe-* database holding
the brief's Alice scenario formed through the real pipeline, then asks the temporal questions. Developer-authored
synthetic text. Run from the repository root: uv run python docs/evaluation/phase-8a/probes/validate_queries.py"""
import re, sys, time, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, "tests/unit")
from test_model_candidate import assertion, response
from gupi import typeql
from gupi.formation import store
from gupi.formation.form import live_schema
from gupi.formation.model_candidate import ModelCandidateV1
from gupi.memory import Memory
from gupi.query import Question
from gupi.records import Batch, Context, Observation, Referent, Source
from gupi.typedb.connection import connect, transaction
from typedb.driver import TransactionType

class Clock:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    def __call__(self): return self.now
O, P, U = "organization", "person", "unclassified"
AL = lambda org: [("employee", "Alice Mercer", P), ("employer", org, O)]
MN = [("subject", "Meridian", O), ("object", "Northstar", O)]
ACQ = lambda t, y: assertion(t, MN, relation="statement", predicate="acquired", times=[(y, "start")])
MSGS = [("a1", "Alice Mercer joined Meridian in 2021.", [assertion("Alice Mercer joined Meridian in 2021", AL("Meridian"), times=[("2021", "start")])]),
        ("a2", "Meridian acquired Northstar in 2022.", [ACQ("Meridian acquired Northstar in 2022", "2022")]),
        ("a3", "Northstar developed Project Atlas.", [assertion("Northstar developed Project Atlas", [("subject", "Northstar", O), ("object", "Project Atlas", U)], relation="statement", predicate="developed")]),
        ("a4", "Alice Mercer left Meridian in 2023.", [assertion("Alice Mercer left Meridian in 2023", AL("Meridian"), times=[("2023", "end")])]),
        ("a5", "Alice Mercer joined Northstar in 2024.", [assertion("Alice Mercer joined Northstar in 2024", AL("Northstar"), times=[("2024", "start")])]),
        ("a6", "Meridian acquired Northstar in 2023, not 2022.", [ACQ("Meridian acquired Northstar in 2023", "2023")]),
        ("a7", "Apologies, please disregard what I wrote about Alice, wrong person.", [])]
d, db, c = connect(), "gupi-probe-" + uuid.uuid4().hex[:8], Clock()
m = Memory.open(db, packs=("core", "people"), driver=d, create=True, clock=c)
utc = lambda y, mo=6: datetime(y, mo, 1, tzinfo=timezone.utc)
try:
    sch, obs_ids = live_schema(m), {}
    for key, text, asserts in MSGS:
        c.now += timedelta(days=30)
        o = Observation("src:p", key, text, c.now, "ctx:p", "p:ivo")
        m.ingest(Batch((Source("src:p", "mail"),), (o,), (Referent("p:ivo", "person", "Ivo Marsh"),), contexts=(Context("ctx:p", "conversation"),)))
        cs, _ = ModelCandidateV1().extract(o, schema=sch, response=response(*asserts) if asserts else response(outcome="no-relevant-assertion"))
        c.now += timedelta(minutes=1)
        store.submit(m, o, cs); obs_ids[key] = o.id
    claims = m.all_claims(); print("claims formed:", len(claims))
    with transaction(d, db, TransactionType.READ) as tx:
        ref = lambda l: typeql.concept_rows(tx, 'match $x isa referent, has label == $l, has gupi-id $i;', {"l": l})[0].get("i").get_string()
        north, alice, meridian = ref("Northstar"), ref("Alice Mercer"), ref("Meridian")
        acq = next(x for x in claims if x.values.get("predicate-text") == "acquired")
        params = {"seed": obs_ids["a2"], "t": c.now, "rid": north, "k": acq.proposition_key, "cid": acq.id}
        blocks = re.findall(r"```typeql\n(.*?)```", Path("docs/evaluation/phase-8a/02-retrieval-design.md").read_text(), re.S)
        for n, q in enumerate(blocks, 1):
            used = {k: v for k, v in params.items() if re.search(rf"(?:==|<=)\s*\${k}\b|, \${k}\)", q)}
            if n == 2: used = {"rid": "p:ivo"}
            t0 = time.perf_counter(); rows = typeql.concept_rows(tx, q, used)
            print(f"Q{n}: {len(rows)} rows, {(time.perf_counter() - t0) * 1000:.1f} ms")
    emp = next(x for x in claims if x.type == "employment" and meridian in x.roles["employer"])
    print("--- employment at Meridian, read across its claims (v2)")
    for label, at in (("mid 2022", utc(2022)), ("start 2022", utc(2022, 1)), ("end 2022", utc(2022, 12)), ("mid 2023", utc(2023)), ("mid 2024", utc(2024))):
        r = m.query(Question("employment", {k: v[0] for k, v in emp.roles.items()}, at, semantics="v2"))
        print(f"{label}: {r.answer.name}; {[b.explanation for b in r.bindings][0][:70]}")
    print("--- the acquisition, two disputed starts (v2)")
    for label, at in (("mid 2022", utc(2022)), ("mid 2023", utc(2023)), ("mid 2024", utc(2024))):
        r = m.query(Question("statement", {k: v[0] for k, v in acq.roles.items()}, at, values={"predicate-text": "acquired"}, semantics="v2"))
        print(f"{label}: {r.answer.name}; {[b.explanation for b in r.bindings][0][:90]}")
finally:
    d.databases.get(db).delete()
