"""Claude-backed extraction (optional: `uv sync --extra claude`). Never the default; every call is budgeted.

Each observation is one Messages API request with a JSON-schema structured output. Before sending, the
worst-case cost is reserved in the ledger (gupi.budget); afterwards each attempt the API reports is charged
at its own model's price. Refusals, truncation and unparseable output produce no claims (recorded as a
rejection), never a guess. The output goes through the same validator as the offline extractor.
"""

import hashlib
import json

from gupi.budget import Attempt, Ledger

MODEL = "claude-opus-5-5"
PROMPT_VERSION = "p1"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SYSTEM = """You extract structured memory from one message. You only propose candidates; a person reviews them later.

Rules:
- Use ONLY the claim types, roles and attributes listed in the request. Prefer a typed claim type. Use the
  generic type "statement" only when no typed type fits, with a short lowercase "predicate" (e.g. "lives in")
  and, if the object is not a named person or organisation, "object_text".
- Every mention "text" and every claim "quote" must be copied exactly from the message.
- "kind" is one of the referent kinds listed; use "unclassified" when unsure.
- "basis": "explicit" if the quoted words state the claim; "inferred" if you concluded it (e.g. resolving
  a pronoun, or reading a relationship from context). Do not invent claims the message does not support.
- Time: copy time phrases exactly as written ("in June", "since 2023", "last month") into time.start and
  time.end. Never convert them to dates and never invent them. Use "" when the message gives none.
  time.ongoing is true only if the message says the claim still holds when written (present tense,
  "still", "now").
- Leave out anything you are not reasonably sure of. Return empty lists if there is nothing to extract."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "mentions": {"type": "array", "items": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "text": {"type": "string"}, "kind": {"type": "string"}},
            "required": ["id", "text", "kind"], "additionalProperties": False}},
        "claims": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "roles": {"type": "array", "items": {
                    "type": "object", "properties": {"role": {"type": "string"}, "mention": {"type": "string"}},
                    "required": ["role", "mention"], "additionalProperties": False}},
                "values": {"type": "array", "items": {
                    "type": "object", "properties": {"attribute": {"type": "string"}, "value": {"type": "string"}},
                    "required": ["attribute", "value"], "additionalProperties": False}},
                "predicate": {"type": "string"},
                "object_text": {"type": "string"},
                "quote": {"type": "string"},
                "basis": {"type": "string", "enum": ["explicit", "inferred"]},
                "confidence": {"type": "number"},
                "time": {"type": "object", "properties": {
                    "start": {"type": "string"}, "end": {"type": "string"}, "ongoing": {"type": "boolean"}},
                    "required": ["start", "end", "ongoing"], "additionalProperties": False},
            },
            "required": ["type", "roles", "values", "predicate", "object_text", "quote", "basis", "confidence", "time"],
            "additionalProperties": False}},
    },
    "required": ["mentions", "claims"],
    "additionalProperties": False,
}


def to_contract(data):
    """Claude's list-shaped output -> the extraction contract's dict shape."""
    claims = []
    for c in data.get("claims", []):
        roles = {}
        for r in c.get("roles", []):
            roles.setdefault(r["role"], []).append(r["mention"])
        claims.append({
            "type": c.get("type"), "roles": roles,
            "values": {v["attribute"]: v["value"] for v in c.get("values", [])},
            "predicate": c.get("predicate") or None, "object_text": c.get("object_text") or None,
            "quote": c.get("quote"), "basis": c.get("basis"), "confidence": c.get("confidence"),
            "time": {"start": (c.get("time") or {}).get("start") or None, "end": (c.get("time") or {}).get("end") or None,
                     "ongoing": bool((c.get("time") or {}).get("ongoing"))},
        })
    return {"mentions": data.get("mentions", []), "claims": claims}


class ClaudeExtractor:
    model = MODEL
    prompt_version = PROMPT_VERSION
    prompt_hash = hashlib.sha256((SYSTEM + json.dumps(OUTPUT_SCHEMA, sort_keys=True)).encode()).hexdigest()[:16]

    def __init__(self, client, ledger: Ledger, model=MODEL, max_tokens=8000, effort="medium", fallbacks=True):
        self.client = client
        self.ledger = ledger
        self.model = model
        self.max_tokens = max_tokens  # includes thinking, which cannot be disabled on this model
        self.effort = effort
        self.fallbacks = fallbacks
        self.method = f"claude:{model}:{PROMPT_VERSION}"
        self.last_problem = None

    @classmethod
    def from_environment(cls, run_cap_usd=None, ledger_database="gupi-ledger", limit_usd=10.0, **kw):
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError("Claude extraction needs the optional dependency: uv sync --extra claude") from e
        from gupi.typedb.connection import connect
        ledger = Ledger(connect(), ledger_database, limit_usd=limit_usd, run_cap_usd=run_cap_usd)
        return cls(anthropic.Anthropic(), ledger, **kw)

    def _request(self, request):
        when = request.observed_at.isoformat() if request.observed_at else "unknown"
        user = (f"Message written at: {when}\n\nAvailable claim types:\n{request.schema.describe()}\n\n"
                f"Referent kinds: {', '.join(sorted(request.schema.referent_types))}\n\nMessage:\n{request.text}")
        params = {
            "model": self.model, "max_tokens": self.max_tokens, "system": SYSTEM,
            "messages": [{"role": "user", "content": user}],
            "output_config": {"effort": self.effort, "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
        }
        if self.fallbacks:
            params.update(betas=[FALLBACK_BETA], fallbacks="default")
        return params

    def extract(self, request):
        params = self._request(request)
        # Upper bound on input tokens: never more tokens than UTF-8 bytes, plus room for request framing.
        max_input = len(json.dumps(params, ensure_ascii=False).encode("utf-8")) + 1000
        call_id, _ = self.ledger.reserve(self.model, "extraction", max_input, self.max_tokens,
                                         fallback_attempts=1 if self.fallbacks else 0)
        try:
            response = self.client.beta.messages.create(**params)
        except Exception:
            self.ledger.fail(call_id)  # sent or not, we cannot prove it was free: keep the reservation
            raise
        self.ledger.settle(call_id, _attempts(response))
        self.last_problem = None
        if response.stop_reason == "refusal":
            self.last_problem = "refusal"
        elif response.stop_reason == "max_tokens":
            self.last_problem = "output truncated at max_tokens"
        if self.last_problem:
            return {"mentions": [], "claims": [], "problem": self.last_problem}
        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
        try:
            return to_contract(json.loads(text))
        except (TypeError, ValueError, KeyError) as e:
            self.last_problem = f"unparseable output: {e}"
            return {"mentions": [], "claims": [], "problem": self.last_problem}


def _attempts(response):
    usage = getattr(response, "usage", None)
    if usage is None:
        return [Attempt(None, None, None)]
    iterations = getattr(usage, "iterations", None) or []
    billed = [i for i in iterations if getattr(i, "type", None) in ("message", "fallback_message")]
    if billed:
        return [Attempt(getattr(i, "model", None), i.input_tokens, i.output_tokens,
                        getattr(i, "cache_creation_input_tokens", 0) or 0, getattr(i, "cache_read_input_tokens", 0) or 0)
                for i in billed]
    return [Attempt(getattr(response, "model", None), usage.input_tokens, usage.output_tokens,
                    getattr(usage, "cache_creation_input_tokens", 0) or 0, getattr(usage, "cache_read_input_tokens", 0) or 0)]
