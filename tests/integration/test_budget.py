"""The fail-closed LLM spending ledger, against the live server (no API calls)."""

import uuid

import pytest
from helpers import Clock

from gupi.budget import Attempt, BudgetExceeded, Ledger, LedgerError, cost_microusd, worst_case_microusd

pytestmark = pytest.mark.integration


@pytest.fixture
def ledger_db(driver):
    name = f"gupi-test-ledger-{uuid.uuid4().hex[:8]}"
    yield name
    if driver.databases.contains(name):
        driver.databases.get(name).delete()


def test_prices_and_worst_case():
    # Opus 5.5 is $4 / $20 per million tokens: 1000 in + 500 out = $0.014
    assert cost_microusd(Attempt("claude-opus-5-5", 1000, 500)) == 14_000
    # An attempt with no model name is charged at the highest known price ($10 / $50)
    assert cost_microusd(Attempt(None, 1000, 500)) == 35_000
    # Worst case: the requested model plus one fallback at the highest price
    assert worst_case_microusd("claude-opus-5-5", 1000, 500) == 14_000 + 35_000
    with pytest.raises(LedgerError):
        worst_case_microusd("claude-unknown-9", 1, 1)


def test_reservations_count_until_settled_and_the_limit_fails_closed(driver, ledger_db):
    ledger = Ledger(driver, ledger_db, limit_usd=0.10, clock=Clock())
    call, reserved = ledger.reserve("claude-opus-5-5", "test", 1000, 500)  # $0.049 worst case
    assert ledger.spent_microusd() == reserved
    actual = ledger.settle(call, [Attempt("claude-opus-5-5", 1000, 500)])
    assert actual == 14_000 and ledger.spent_microusd() == 14_000

    ledger.reserve("claude-opus-5-5", "test", 1000, 500)  # 0.014 + 0.049 = 0.063
    with pytest.raises(BudgetExceeded):
        ledger.reserve("claude-opus-5-5", "test", 1000, 500)  # would reach 0.112 > 0.10
    # A fresh process sees the same spending: the ledger is persistent, not in memory.
    assert Ledger(driver, ledger_db, limit_usd=0.10).spent_microusd() == 63_000


def test_unknown_outcomes_keep_the_reservation_and_only_proven_non_sends_release_it(driver, ledger_db):
    ledger = Ledger(driver, ledger_db, limit_usd=1.0, clock=Clock())
    a, ra = ledger.reserve("claude-opus-5-5", "test", 1000, 500)
    b, rb = ledger.reserve("claude-opus-5-5", "test", 2000, 500)
    c, _ = ledger.reserve("claude-opus-5-5", "test", 3000, 500)
    ledger.fail(a)                                                   # network error: outcome unknown
    ledger.settle(b, [Attempt("claude-opus-5-5", None, None)])       # usage missing: also unknown
    ledger.fail(c, "failed-before-send")                             # never sent: released
    assert ledger.spent_microusd() == ra + rb


def test_fallback_attempts_are_each_charged_at_their_own_model(driver, ledger_db):
    ledger = Ledger(driver, ledger_db, limit_usd=1.0, clock=Clock())
    call, _ = ledger.reserve("claude-opus-5-5", "test", 1000, 500)
    actual = ledger.settle(call, [Attempt("claude-opus-5-5", 1000, 0), Attempt("claude-opus-4-8", 1000, 500)])
    assert actual == 4_000 + (5_000 + 12_500)


def test_run_cap_and_limit_changes_are_explicit(driver, ledger_db):
    ledger = Ledger(driver, ledger_db, limit_usd=10.0, run_cap_usd=0.05, clock=Clock())
    ledger.reserve("claude-opus-5-5", "test", 1000, 500)
    with pytest.raises(BudgetExceeded, match="run cap"):
        ledger.reserve("claude-opus-5-5", "test", 1000, 500)
    with pytest.raises(LedgerError, match="explicitly"):
        Ledger(driver, ledger_db, limit_usd=20.0)  # a different limit is never applied silently
    ledger.set_limit(20.0)
    assert Ledger(driver, ledger_db, limit_usd=20.0).limit == 20_000_000
