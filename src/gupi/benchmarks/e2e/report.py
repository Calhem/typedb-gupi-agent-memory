"""Aggregate tables for a Phase 6D run, generated from its raw files (never edited by hand).

    uv run python -I -m gupi.benchmarks.e2e.report first-run   # writes docs/evaluation/phase-6d/first-run/aggregate.md
"""

import json
import sys
from pathlib import Path

from gupi.benchmarks.e2e import manifest

OUT = manifest.OUT.parent


def _load(label, part):
    p = OUT / label / f"{part}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _f(x, d=3):
    return "—" if x is None else (f"{x:.{d}f}" if isinstance(x, float) else str(x))


def world_tables(w):
    out = ["## D1 answers (15 frozen questions; Phase 4 world)", "",
           "| System | Kind | Correct | Incorrect | Missing | Abstained when it should (of 6) | Unsupported definitive (gold abstains or contested / evidence not direct) | Citation P / R | p50 / p95 s |",
           "|---|---|---|---|---|---|---|---|---|"]
    kinds = {"gupi-e2e": "answers, end to end", "gupi-e2e-policy": "answers, end to end, no reviewer",
             "gupi-gold": "answers on gold claims (diagnostic)", "gupi-rules-v1": "answers, Phase 4 pipeline (diagnostic)",
             "keyword-answer": "answers, keyword heuristic"}
    for name, s in w["systems"].items():
        fz, parts = s["frozen_scorer"], s["unsupported_definitive_parts"]
        out.append(f"| {name} | {kinds[name]} | {s['correct']}/{s['questions']} | {s['incorrect']} | {s['missing']} | "
                   f"{fz['abstention']['correct']}/{fz['abstention']['of']} | {parts['definitive_where_gold_abstains_or_contested']} / "
                   f"{parts['definitive_on_evidence_not_direct']} | {_f(fz['citation_precision'])} / {_f(fz['citation_recall'])} | "
                   f"{_f(s['latency']['p50'], 4)} / {_f(s['latency']['p95'], 4)} |")
    out += ["| keyword, embedding, hybrid, hybrid-unfiltered, structured | evidence only | not evaluated | | | | | | |", "",
            "### By category (correct / questions)", "", "| System | " + " | ".join(
                c for c in ("temporal-status", "contradiction", "abstention", "belief-time", "open-role")) + " |",
            "|---|---|---|---|---|---|"]
    for name, s in w["systems"].items():
        out.append(f"| {name} | " + " | ".join(
            f"{s['by_category'].get(c, {}).get('correct', 0)}/{s['by_category'].get(c, {}).get('of', 0)}"
            for c in ("temporal-status", "contradiction", "abstention", "belief-time", "open-role")) + " |")
    out += ["", "### Per question", "", "| Question | Gold | " + " | ".join(w["systems"]) + " |",
            "|---|---|" + "---|" * len(w["systems"])]
    rows = {n: {r["id"]: r for r in s["rows"]} for n, s in w["systems"].items()}
    for r in next(iter(w["systems"].values()))["rows"]:
        out.append(f"| {r['id']} | {r['gold']}{' (' + r['gold_binding'] + ')' if r['gold_binding'] else ''} | " + " | ".join(
            f"{'✓' if rows[n][r['id']]['correct'] else '✗'} {rows[n][r['id']]['got']}"
            + (f" ({', '.join(rows[n][r['id']]['binding'])})" if rows[n][r['id']]['binding'] else "") for n in w["systems"]) + " |")
    rs = w["retrieval"]["summary"]
    out += ["", "## D1 evidence retrieval (message units; 9 questions with gold evidence; 11 messages in all)", "",
            "| System | R@1 | R@5 | R@10 | P@5 | p50 s |", "|---|---|---|---|---|---|"]
    for name, s in rs.items():
        out.append(f"| {name} | {_f(s['recall@1'])} | {_f(s['recall@5'])} | {_f(s['recall@10'])} | {_f(s['precision@5'])} | "
                   f"{_f(s['latency']['p50'], 4)} |")
    fz = w["systems"]["gupi-e2e"]["frozen_scorer"]
    es = w["evidence_states"]
    out += [f"| gupi-e2e citations (unranked set) | set precision {_f(fz['citation_precision'])}, set recall "
            f"{_f(fz['citation_recall'])} | | | | |", "",
            f"Gold evidence messages (one count per question and message, {sum(es[k] for k in ('cited', 'formed_not_cited', 'candidate_only', 'text_only'))} in all): cited {es['cited']}, formed but not cited "
            f"{es['formed_not_cited']}, stored candidate only {es['candidate_only']}, original text only {es['text_only']}.", ""]
    return out


def formation_tables(d1, d2, d3):
    out = ["## Formation (layer A)", ""]
    if d2:
        t = d2["totals"]
        out += ["### D2 Phase 2 held-out (independent; 12 messages, 12 gold claims; no reviewer)", "",
                "| Measure | Count |", "|---|---|",
                f"| candidate precision | {t['matched']}/{t['extracted']} |", f"| candidate recall | {t['matched']}/{t['expected']} |",
                f"| participant (entity) precision | {t['mentions_matched']}/{t['mentions_extracted']} |",
                f"| participant (entity) recall | {t['mentions_matched']}/{t['mentions_gold']} |",
                f"| relation: extracted candidates with the right type and roles (matching requires both, so this equals precision) | {t['matched']}/{t['extracted']} |",
                f"| start window exact, of matched | {t['start_correct']}/{t['time_scored']} |",
                f"| end window and ongoing exact, of matched | {t['end_correct']}/{t['time_scored']} |",
                f"| both exact, of matched | {t['both_correct']}/{t['time_scored']} |",
                f"| gold claims as accepted claims in TypeDB | {t['accepted_claim']}/{t['expected']} |",
                f"| gold claims as stored candidates only | {t['candidate_only']}/{t['expected']} |",
                f"| gold claims absent | {t['absent']}/{t['expected']} |",
                f"| policy decisions (first) | {d2['policy_outcomes']} |", ""]
    if d3:
        fz = d3["frozen_scorer"]
        out += ["### D3 frozen 6B set (implementer-written; development-adjacent)", "", "| Measure | Count |", "|---|---|",
                f"| candidate precision | {fz['matched']}/{fz['extracted']} |", f"| candidate recall | {fz['matched']}/{fz['expected']} |",
                f"| correct rejections | {fz['correct_rejections']}/{fz['empty_passages']} |"]
        out += [f"| {f}, of matched | {v['correct']}/{v['of']} |" for f, v in fz["fields"].items()]
        rep = d3["representation"]
        out += [f"| expected candidates as accepted claims | {rep['accepted_claim']}/{fz['expected']} |",
                f"| as stored candidates only (withheld or waiting for review) | {rep['candidate_only']}/{fz['expected']} |",
                f"| absent | {rep['absent']}/{fz['expected']} |", f"| policy decisions (first) | {d3['policy_outcomes']} |", ""]
    if d1:
        db = d1["databases"]["gupi-e2e"]
        out += [f"D1 end to end: {db['memory-candidate']} candidates stored, {db['formation-decision']} decisions, "
                f"{db['formed-into']} formed; reviewer actions {len(db['reviews'])}.", ""]
    return out


def adversarial_tables(a):
    s = a["summary"]
    return ["## D4 adversarial (development tests only; through the candidate store)", "", "| Measure | Result |", "|---|---|"] + [
        f"| {k} | {v} |" for k, v in s.items() if k != "latency"] + [""]


def conversational_tables(name, r, phase5=None):
    out = [f"## {name}: evidence retrieval only (not an official score; no answers generated)", ""]
    f = r["formation"]
    out += [f"Formation: {f['observations']} turns, {f['candidates']} candidates from {f['with_candidates']} turns; "
            f"{f['observations_with_domain_verb']} turns contain a domain verb; {f['unparsed_in_domain_sentences']} "
            f"in-domain sentences not parsed; policy decisions {f['policy_outcomes']}.", ""]
    for unit, systems in r["summary"].items():
        out += [f"| {unit} | R@1 | R@5 | R@10 | P@5 | MRR | empty | p50 / p95 s |", "|---|---|---|---|---|---|---|---|"]
        for sname, s in systems.items():
            o = s["overall"]
            out.append(f"| {sname} | {_f(o['recall@1'])} | {_f(o['recall@5'])} | {_f(o['recall@10'])} | "
                       f"{_f(r['precision@5'][unit][sname])} | {_f(o['mrr'])} | {s['empty_results']} | "
                       f"{_f(s['latency_seconds']['median'], 3)} / {_f(s['latency_seconds']['p95'], 3)} |")
        cats = sorted({c for s in systems.values() for c in s["by_category"]})
        out += ["", f"{unit} R@5 by category: " + "; ".join(
            f"{c} ({next(iter(systems.values()))['by_category'][c]['questions']}): " + " / ".join(
                f"{sn} {_f(s['by_category'][c]['recall@5'])}" for sn, s in systems.items()) for c in cats), ""]
    a = r["attribution_structured_arm"]
    out += [f"GUPI structured arm, earliest stage per question ({a['questions']}): {a['by_stage']}; gold-turn states: {a['turn_states']}.", ""]
    if r.get("reproduction"):
        rp = r["reproduction"]
        out += [f"Reproduction against {rp['compared_with']}: {rp['identical']} rows identical, {rp['different']} different, "
                f"{rp['not_in_phase5']} not in Phase 5.", ""]
    return out


def main(argv=None):
    args = argv or sys.argv[1:]
    label = args[0]
    target = Path(args[1]) if len(args) > 1 else OUT / label / "aggregate.md"
    d1, d2, d3 = _load(label, "world"), _load(label, "phase2"), _load(label, "frozen-6b")
    lines = [f"# Phase 6D aggregate tables: `{label}`", "",
             "Generated by `python -m gupi.benchmarks.e2e.report` from the raw files in this folder. "
             "Evidence-only systems have no answer accuracy.", ""]
    if d1:
        lines += world_tables(d1)
    lines += formation_tables(d1, d2, d3)
    if (a := _load(label, "adversarial")):
        lines += adversarial_tables(a)
    if (lo := _load(label, "locomo-heldout")) and "failed" not in lo:
        lines += conversational_tables("D5 LoCoMo held-out", lo)
    if (lx := _load(label, "longmemeval-extraction")) and "failed" not in lx:
        lines += ["## D6 LongMemEval held-out: extraction only (no TypeDB)", "",
                  f"{lx['questions']} questions, {lx['turns']} turns: {lx['candidates']} candidates from "
                  f"{lx['turns_with_candidates']} turns ({lx['candidate_kinds']}); {lx['turns_with_domain_verb']} turns "
                  f"contain a domain verb; answer turns {lx['answer_turns']}, of which {lx['answer_turns_with_candidates']} "
                  f"gave a candidate; {lx['turns_per_second']} turns/s.", ""]
    if (ls := _load(label, "longmemeval-subset")) and "failed" not in ls:
        lines += conversational_tables("D6 LongMemEval held-out subset (64)", ls)
    if (sc := _load(label, "scale")) and "failed" not in sc:
        lines += ["## Operational probe (synthetic load; no accuracy)", "",
                  "| copies | observations | candidates | claims | pending | pending() s | query p50 / p95 s | submit s/obs | DB MB |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for s in sc["steps"]:
            lines.append(f"| {s['copies']} | {s['observations']} | {s['candidates']} | {s['claims']} | {s['pending']} | "
                         f"{s['pending_seconds']} | {s['query_latency']['p50']} / {s['query_latency']['p95']} | "
                         f"{s['last_copy']['submit_s_per_obs']} | {_f(s['database_bytes'] / 1e6 if s['database_bytes'] else None, 1)} |")
        rs = sc["resubmission"]
        lines += ["", f"Resubmitting {rs['submissions']} observations took {rs['seconds']} s and wrote decisions "
                  f"{rs['decisions_before']}→{rs['decisions_after']}, candidates {rs['candidates_before']}→{rs['candidates_after']}, "
                  f"claims {rs['claims_before']}→{rs['claims_after']}.", ""]
    failed = [p.stem for p in (OUT / label).glob("*.json") if "failed" in json.loads(p.read_text())]
    if failed:
        lines += [f"**Failed parts (recorded, not rerun under this label):** {', '.join(sorted(failed))}.", ""]
    target.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
