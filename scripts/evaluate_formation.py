"""Phase 6B extraction evaluation with the rules:v1 comparison (docs/evaluation/phase-6b-extraction.md).

    uv run python -I scripts/evaluate_formation.py --json docs/evaluation/phase-6b-extraction-first-run.json

The comparison runs rules:v1 through the production extraction contract. That is why it lives here, outside
the gupi.formation package, which imports nothing from the production pipeline.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gupi.formation import evaluation  # noqa: E402


def rules_v1_claims():
    """rules:v1 through the existing contract validator, for comparison only (no TypeDB)."""
    from gupi.extraction.contract import SchemaInfo, validate
    from gupi.extraction.pipeline import ExtractionRequest
    from gupi.extraction.rules import RuleExtractor
    person, org = frozenset({"person"}), frozenset({"organization"})
    schema = SchemaInfo(frozenset({"person", "organization"}),
                        {"employment": {"employee": person, "employer": org}, "reporting": {"report": person, "manager": person},
                         "statement": {"subject": person, "object": person | org}},
                        {"employment": frozenset({"job-title"})})

    def extract(obs, prior):
        raw = RuleExtractor().extract(ExtractionRequest(obs.content, obs.observed_at, schema))
        out = validate(raw, obs, schema, "scope", "rules:v1")
        surface = {m.referent_id: m.surface for m in out.mentions}
        return [(c.type, {r: surface[v if isinstance(v, str) else v[0]] for r, v in c.roles.items()}, "positive")
                for c in out.claims if c.type != "statement"]
    return extract



if __name__ == "__main__":
    evaluation.main(extra={f"rules:v1/{s}": evaluation.score_conversations(s, rules_v1_claims()) for s in ("heldout", "dev")})
