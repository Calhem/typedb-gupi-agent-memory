"""LLM usage and cost tracking with a fail-closed spending limit (docs/adr/0005).

The ledger lives in TypeDB, in its own database (default `gupi-ledger`) shared by every run, so starting a
new memory database never resets what has been spent. Amounts are integer micro-dollars.

Every call follows reserve -> call -> settle:
- `reserve` commits a worst-case charge BEFORE the request is sent, and refuses (BudgetExceeded) if that
  would take spending past the limit (or past an optional per-run cap).
- `settle` replaces the reservation with the actual cost of every attempt the API reports.
- `fail` keeps the full reservation as spent when the outcome is unknown (network error, missing usage).
Spent = settled actual costs + every reservation not settled. Anything unexpected (unknown model, unreadable
ledger, limit mismatch) stops calls rather than letting them through.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from typedb.driver import TransactionType

from gupi import migrations, typeql
from gupi.typedb.connection import transaction

# USD per million tokens (input, output), from Anthropic's published first-party prices as cached in the
# Claude API reference on 2026-10-06. Update deliberately; a model missing here cannot be called.
PRICES_USD_PER_MTOK = {
    "claude-fable-5-1": (10.00, 50.00),
    "claude-fable-5": (10.00, 50.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-5-5": (0.50, 2.50),   # the >100K-token rate, to stay on the safe side
    "claude-haiku-4-5": (1.00, 5.00),
}
# Server-side fallbacks may route to a model we cannot predict, so worst cases use the highest price.
MAX_PRICE = (max(p[0] for p in PRICES_USD_PER_MTOK.values()), max(p[1] for p in PRICES_USD_PER_MTOK.values()))
CACHE_WRITE_FACTOR = 2.0  # charged above the real 1.25x-2x cache-write premium, never below


class BudgetExceeded(Exception):
    """The call was not made: its worst-case cost would exceed the spending limit or the run cap."""


class LedgerError(Exception):
    """The ledger could not be read or is inconsistent; no call may be made."""


@dataclass(frozen=True)
class Attempt:
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0


def usd_to_micro(usd):
    return round(usd * 1_000_000)


def price(model):
    if model not in PRICES_USD_PER_MTOK:
        raise LedgerError(f"no price known for model {model!r}; add it to PRICES_USD_PER_MTOK first")
    return PRICES_USD_PER_MTOK[model]


def cost_microusd(attempt: Attempt):
    """Actual cost of one attempt. A missing model is charged at the highest known price."""
    if attempt.input_tokens is None or attempt.output_tokens is None:
        raise LedgerError("attempt has no token counts")
    p_in, p_out = PRICES_USD_PER_MTOK.get(attempt.model, MAX_PRICE)
    # USD per Mtok == micro-USD per token
    return round(attempt.input_tokens * p_in + attempt.output_tokens * p_out
                 + attempt.cache_write_tokens * p_in * CACHE_WRITE_FACTOR + attempt.cache_read_tokens * p_in)


def worst_case_microusd(model, max_input_tokens, max_output_tokens, fallback_attempts=1):
    """The most one request can cost: the requested model plus each possible fallback at the highest price."""
    p_in, p_out = price(model)
    first = max_input_tokens * p_in + max_output_tokens * p_out
    return round(first + fallback_attempts * (max_input_tokens * MAX_PRICE[0] + max_output_tokens * MAX_PRICE[1]))


class Ledger:
    LIMIT_ID = "total"

    def __init__(self, driver, database="gupi-ledger", limit_usd=10.0, run_cap_usd=None, clock=None):
        self.driver = driver
        self.database = database
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.run_cap = usd_to_micro(run_cap_usd) if run_cap_usd is not None else None
        self.run_spent = 0
        try:
            if not driver.databases.contains(database):
                driver.databases.create(database)
            migrations.migrate(driver, database, ["ledger"])
            self.limit = self._ensure_limit(usd_to_micro(limit_usd))
        except LedgerError:
            raise
        except Exception as e:
            raise LedgerError(f"ledger database {database!r} is unavailable: {e}") from e

    def _ensure_limit(self, wanted):
        with transaction(self.driver, self.database, TransactionType.WRITE) as tx:
            docs = typeql.documents(tx, 'match $l isa spending-limit, has ledger-id == $id; fetch { "v": $l.limit-microusd };',
                                    {"id": self.LIMIT_ID})
            if not docs:
                typeql.run(tx, "insert $l isa spending-limit, has ledger-id == $id, has limit-microusd == $v, "
                               "has ledger-at == $at;", {"id": self.LIMIT_ID, "v": wanted, "at": self.clock()})
                return wanted
        stored = docs[0]["v"]
        if stored != wanted:
            raise LedgerError(f"the ledger's limit is ${stored / 1e6:.2f}, not ${wanted / 1e6:.2f}; "
                              "changing a spending limit must be done explicitly (set_limit)")
        return stored

    def set_limit(self, limit_usd):
        """Change the limit explicitly (an owner decision)."""
        with transaction(self.driver, self.database, TransactionType.WRITE) as tx:
            typeql.run(tx, "match $l isa spending-limit, has ledger-id == $id; update $l has limit-microusd == $v;",
                       {"id": self.LIMIT_ID, "v": usd_to_micro(limit_usd)})
        self.limit = usd_to_micro(limit_usd)

    @staticmethod
    def _spent(tx):
        def total(q):
            rows = typeql.concept_rows(tx, q)
            value = rows[0].get("s") if rows else None
            return value.get_integer() if value is not None and value.is_integer() else 0
        settled = total('match $c isa llm-call, has call-outcome "settled", has actual-microusd $a; reduce $s = sum($a);')
        open_ = total('match $c isa llm-call, has call-outcome $o, has reserved-microusd $r; '
                      'not { $o == "settled"; }; not { $o == "failed-before-send"; }; reduce $s = sum($r);')
        return settled + open_

    def spent_microusd(self):
        try:
            with transaction(self.driver, self.database, TransactionType.READ) as tx:
                return self._spent(tx)
        except Exception as e:
            raise LedgerError(f"cannot read the ledger: {e}") from e

    def remaining_usd(self):
        return (self.limit - self.spent_microusd()) / 1e6

    def reserve(self, model, purpose, max_input_tokens, max_output_tokens, fallback_attempts=1):
        amount = worst_case_microusd(model, max_input_tokens, max_output_tokens, fallback_attempts)
        if self.run_cap is not None and self.run_spent + amount > self.run_cap:
            raise BudgetExceeded(f"run cap ${self.run_cap / 1e6:.2f} reached (this call could cost ${amount / 1e6:.4f})")
        now = self.clock()
        call_id = f"llm-call:{uuid.uuid4().hex}"  # each call is a separate event, never deduplicated
        with transaction(self.driver, self.database, TransactionType.WRITE) as tx:
            spent = self._spent(tx)
            if spent + amount > self.limit:
                raise BudgetExceeded(f"spent ${spent / 1e6:.4f} of ${self.limit / 1e6:.2f}; "
                                     f"this call could cost up to ${amount / 1e6:.4f}")
            typeql.run(tx, "insert $c isa llm-call, has ledger-id == $id, has llm-model == $m, has call-purpose == $p, "
                           "has reserved-microusd == $r, has call-outcome \"reserved\", has ledger-at == $at;",
                       {"id": call_id, "m": model, "p": purpose, "r": amount, "at": now})
        self.run_spent += amount
        return call_id, amount

    def settle(self, call_id, attempts):
        """Record actual usage. If any attempt lacks token counts, the full reservation stays spent."""
        try:
            actual = sum(cost_microusd(a) for a in attempts)
        except LedgerError:
            return self.fail(call_id, "failed-unknown-usage")
        tokens_in = sum(a.input_tokens for a in attempts)
        tokens_out = sum(a.output_tokens for a in attempts)
        with transaction(self.driver, self.database, TransactionType.WRITE) as tx:
            reserved = self._reserved(tx, call_id)
            typeql.run(tx, "match $c isa llm-call, has ledger-id == $id; update $c has call-outcome \"settled\"; "
                           "insert $c has actual-microusd == $a, has input-tokens == $i, has output-tokens == $o;",
                       {"id": call_id, "a": actual, "i": tokens_in, "o": tokens_out})
        self.run_spent += actual - reserved
        return actual

    def fail(self, call_id, outcome="failed-unknown-usage"):
        """`failed-before-send` releases the reservation (the request provably never left); anything else keeps it."""
        with transaction(self.driver, self.database, TransactionType.WRITE) as tx:
            reserved = self._reserved(tx, call_id)
            typeql.run(tx, "match $c isa llm-call, has ledger-id == $id; update $c has call-outcome == $o;",
                       {"id": call_id, "o": outcome})
        if outcome == "failed-before-send":
            self.run_spent -= reserved
        return reserved if outcome != "failed-before-send" else 0

    @staticmethod
    def _reserved(tx, call_id):
        docs = typeql.documents(tx, 'match $c isa llm-call, has ledger-id == $id; fetch { "r": $c.reserved-microusd };',
                                {"id": call_id})
        if not docs:
            raise LedgerError(f"unknown ledger entry {call_id}")
        return docs[0]["r"]
