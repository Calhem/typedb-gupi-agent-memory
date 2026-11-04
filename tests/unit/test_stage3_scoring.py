"""The Stage 3 scorer on small synthetic fixtures (tests/stage3_synthetic.py), never on the evaluation
corpus: false positives and negatives, duplicates, attribution and claimant-kind errors, unresolved and
guessed correction targets, forwarding, pipeline outcomes, the bundle and the transcript audit."""

import dataclasses
import json
import sys
from pathlib import Path

import pytest

from gupi.benchmarks.phase7b import harness, stage3

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures"))
import stage3_synthetic as syn  # noqa: E402


def fresh(tmp_path):
    d = tmp_path / f"run{len(list(tmp_path.iterdir()))}"
    d.mkdir()
    return d


def scored(tmp_path, formed=None, mutate=None, **changes):
    pub, priv, resp = syn.write(fresh(tmp_path), syn.responses(**changes))
    passages, gold, categories = stage3.load(pub, priv)
    raw, _, _ = stage3.read_responses(resp, passages)
    extracted = harness.extract(stage3.harness_rows(passages), stage3.MODEL_METHOD, raw)
    if mutate:
        mutate(extracted)
    return stage3.evaluate(passages, gold, extracted, categories, formed(extracted) if formed else None), extracted


def kinds(r):
    return r["severe_errors"]["by_kind"]


def cand(extracted, pid):
    return extracted[pid][1].candidates[0]


def replace(extracted, pid, **attribution_or_fields):
    obs, cset, out, fl = extracted[pid]
    c = cset.candidates[0]
    if "attribution" in attribution_or_fields:
        c = dataclasses.replace(c, attribution=dataclasses.replace(c.attribution, **attribution_or_fields.pop("attribution")))
    c = dataclasses.replace(c, **attribution_or_fields)
    extracted[pid] = (obs, dataclasses.replace(cset, candidates=(c,) + cset.candidates[1:]), out, fl)


def test_correct_responses_score_cleanly(tmp_path):
    r, _ = scored(tmp_path)
    s, i = r["summary"], r["integrity"]
    assert (s["precision"]["k"], s["precision"]["n"], s["recall"]["k"], s["recall"]["n"]) == (9, 9, 9, 9)
    assert r["severe_errors"]["count"] == 0 and not r["adjudicate"]
    assert i["claimant_kind"]["k"] == i["claimant_kind"]["n"] == 3          # a person, two unknown forward senders
    assert i["forwarding_origin"]["k"] == i["forwarding_origin"]["n"] == 2
    assert i["correction_target"]["k"] == i["correction_target"]["n"] == 2   # one resolved, one left unestablished
    assert r["by_category"]["synthetic"] == {"passages": 10, "gold": 9, "matched": 9}


def test_a_false_positive_on_a_negative_control(tmp_path):
    fp = syn.response(syn.assertion("update on Corvan Freight", [("subject", "Corvan Freight", "organization")],
                                    relation="statement", predicate="update"))
    r, _ = scored(tmp_path, **{"S-08": fp})
    assert r["summary"]["counts"]["unsupported"] == 1 and r["summary"]["precision"]["n"] == 10
    assert kinds(r) == {"invented assertion": 1}
    formed = lambda x: {"statuses": {c.id: "formed" for _, cs, _, _ in x.values() for c in cs.candidates}, "superseded": 0}
    r, _ = scored(tmp_path, formed=formed, **{"S-08": fp})
    assert kinds(r)["unsupported definitive assertion"] == 1               # the same false positive, formed


def test_a_false_negative_is_a_miss(tmp_path):
    r, _ = scored(tmp_path, **{"S-01": syn.response(outcome="no-relevant-assertion")})
    assert r["summary"]["recall"]["k"] == 8 and r["pipeline"]["extraction_outcomes"]["no-relevant-assertion"] == 2
    assert next(p for p in r["passages"] if p["passage"] == "S-01")["missed"] == ["S-01-a1"]


def test_a_duplicate_is_counted_apart_from_false_positives(tmp_path):
    again = syn.assertion("Ilse Varga joined Corvan Freight", syn.emp("Corvan Freight"))
    r, _ = scored(tmp_path, **{"S-01": syn.response(syn.CORRECT["S-01"]["assertions"][0], again)})
    c = r["summary"]["counts"]
    assert (c["duplicates"], c["unsupported"], r["summary"]["precision"]["n"]) == (1, 0, 9)


def test_attribution_errors(tmp_path):
    dropped = syn.assertion("Ilse Varga reports to Piet Marr", [("report", "Ilse Varga", "person"), ("manager", "Piet Marr", "person")],
                            relation="reporting")
    r, _ = scored(tmp_path, **{"S-02": syn.response(dropped)})
    assert r["integrity"]["claimant"]["k"] == 8 and "unsupported certainty" in kinds(r)   # reported shown as direct


def test_an_invented_claimant_and_kind(tmp_path):
    invented = syn.assertion("Ilse Varga joined Corvan Freight as general counsel in May 2025", syn.emp("Corvan Freight"),
                             times=[("May 2025", "start")], title="general counsel", claimant="Corvan Freight",
                             claimant_kind="organisation", mode="reported")
    r, _ = scored(tmp_path, **{"S-01": syn.response(invented)})
    assert {"invented claimant", "invented claimant kind"} <= set(kinds(r))


def test_a_wrong_claimant_kind(tmp_path):
    org = syn.assertion("Ilse Varga reports to Piet Marr", [("report", "Ilse Varga", "person"), ("manager", "Piet Marr", "person")],
                        relation="reporting", claimant="Tamsin Oduya", claimant_kind="organisation", mode="reported")
    r, _ = scored(tmp_path, **{"S-02": syn.response(org)})
    assert kinds(r) == {"invented claimant kind": 1} and r["integrity"]["claimant_kind"]["k"] == 2


def test_an_unresolved_correction_must_stay_unresolved(tmp_path):
    r, x = scored(tmp_path)
    assert cand(x, "S-07").relations[0].target is None                  # two earlier statements: not established
    assert cand(x, "S-04").relations[0].target == cand(x, "S-03").id    # one earlier statement: resolved

    def guess(extracted):
        rel = cand(extracted, "S-07").relations[0]
        replace(extracted, "S-07", relations=(dataclasses.replace(rel, target=cand(extracted, "S-06").id),))
    r, _ = scored(tmp_path, mutate=guess)
    assert kinds(r) == {"guessed correction target": 1} and r["integrity"]["correction_target"]["k"] == 1


def test_a_forward_presented_as_first_hand(tmp_path):
    r, _ = scored(tmp_path, mutate=lambda x: replace(x, "S-09", attribution={"mode": "direct", "via": (), "transmission": ()}))
    assert "forwarded presented as first-hand" in kinds(r) and r["integrity"]["forwarding_origin"]["k"] == 1


def test_pipeline_errors_are_kept_apart(tmp_path):
    def formed(x):
        st = {c.id: "formed" for _, cs, _, _ in x.values() for c in cs.candidates}
        st[cand(x, "S-07").id] = "review"
        return {"statuses": st, "reasons": {}, "store_invalid": [{"passage": "S-01", "candidate": None, "reason": "schema"}],
                "failures": [{"passage": "S-03", "error": "ValueError: x"}], "superseded": 1}
    r, x = scored(tmp_path, formed=formed)
    p, k = r["pipeline"], kinds(r)
    assert p["formation"] == {"formed": 8, "review": 1, "withheld": 0, "rejected": 0}
    assert p["validator_rejections"] == {"extractor": 0, "store": 1} and len(p["formation_failures"]) == 1
    assert p["duplicate_original_attestations"] == 1                       # S-10, a forwarded copy, formed
    assert k["correction formed without review"] == 1 and k["correction applied automatically"] == 1
    assert "unsupported definitive assertion" not in k                    # every formed claim matches gold
    assert sorted(d["gold"] for d in p["admission_disagreements"]) == ["S-04-a1", "S-10-a1"]   # pipeline, not extraction
    assert r["integrity"]["independent_corroboration"]["k"] == 8 and r["severe_errors"]["formed"] == 1


def test_missing_and_malformed_responses_are_invalid_outputs_never_repaired(tmp_path):
    raw = syn.responses(**{"S-01": "not json {"})
    del raw["S-02"]
    raw["S-99"] = "{}"
    pub, priv, resp = syn.write(tmp_path, raw)
    passages, gold, _ = stage3.load(pub, priv)
    found, hashes, extra = stage3.read_responses(resp, passages)
    assert found["S-02"] is None and found["S-01"] == "not json {" and extra == ["S-99.json"] and len(hashes) == 9
    r = stage3.evaluate(passages, gold, harness.extract(stage3.harness_rows(passages), stage3.MODEL_METHOD, found))
    assert r["pipeline"]["extraction_outcomes"]["invalid-model-output"] == 2 and r["summary"]["recall"]["k"] == 7


def test_structural_checks(tmp_path):
    bad_passage = dict(syn.PASSAGES[0], text="changed")
    assert any("sha256" in p for p in stage3.check_passages([bad_passage]))
    no_kind = [dict(g, original_claimant_kind="") if g["assertion_id"] == "S-02-a1" else g for g in syn.GOLD]
    assert any("original_claimant_kind" in p for p in stage3.check_gold(no_kind, syn.PASSAGES))
    assert stage3.check_gold(syn.GOLD, syn.PASSAGES) == [] and stage3.check_passages(syn.PASSAGES) == []


def test_the_bundle_holds_only_public_files(tmp_path):
    pub, priv, _ = syn.write(tmp_path)
    out = tmp_path / "bundle"
    hashes = stage3.bundle(pub, out)
    found = sorted(str(f.relative_to(out)) for f in out.rglob("*") if f.is_file())
    assert found == sorted(list(stage3.BUNDLE_FILES) + [".claude/settings.json"]) and set(hashes) == set(found)
    assert (out / "responses").is_dir() and not any("gold" in f or "categories" in f for f in found)
    with pytest.raises(FileExistsError):
        stage3.bundle(pub, out)


def transcript(tmp_path, *calls):
    d = tmp_path / "transcripts"
    d.mkdir(exist_ok=True)
    lines = [json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": n, "input": i}]}})
             for n, i in calls]
    (d / "session.jsonl").write_text("\n".join(lines) + "\n")
    return d


def test_the_audit_accepts_only_bundle_reads_and_writes(tmp_path):
    b = tmp_path / "bundle"
    b.mkdir()
    ok = transcript(tmp_path, ("Read", {"file_path": str(b / "passages.jsonl")}), ("Write", {"file_path": str(b / "responses/X.json")}))
    assert stage3.audit(ok, b)["valid"]
    bad = transcript(fresh(tmp_path),
                     ("Read", {"file_path": str(tmp_path / "private" / "gold.jsonl")}), ("Bash", {"command": "ls"}),
                     ("Read", {"file_path": str(b / ".." / "private" / "gold.jsonl")}))
    v = stage3.audit(bad, b)
    assert not v["valid"] and [x["problem"] for x in v["violations"]] == ["outside the bundle", "tool not allowed", "outside the bundle"]
    twice = transcript(fresh(tmp_path), ("Write", {"file_path": str(b / "responses/X.json")}),
                       ("Write", {"file_path": str(b / "responses/X.json")}), ("Edit", {"file_path": str(b / "responses/X.json")}))
    assert [x["problem"] for x in stage3.audit(twice, b)["violations"]] == ["response rewritten", "tool not allowed"]
    empty = tmp_path / "none"
    empty.mkdir()
    assert not stage3.audit(empty, b)["valid"]                     # no transcript: nothing proves the isolation
