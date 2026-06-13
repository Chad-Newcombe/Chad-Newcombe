"""Tests for the pure-Python finance logic (parser, analyzer, debt math, budget).

These tests require no API key — they exercise the deterministic computation only.
Run with: pytest tests/
"""

from __future__ import annotations
import csv
from pathlib import Path

import pytest

from src.finance.parser import parse_csv_statement, _parse_amount, _parse_date, _clean_float
from src.finance.analyzer import (
    compute_financial_snapshot,
    compute_avalanche_plan,
    compute_snowball_plan,
    compute_budget_framework,
    default_monthly_budget,
)
from src.models.finance import (
    BankAccount,
    CreditCardAccount,
    Transaction,
    TransactionCategory,
)


# ── Parser ────────────────────────────────────────────────────────────────────

def _write_csv(path: Path, headers: list[str], rows: list[list]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def test_parse_standard_bank_csv(tmp_path):
    p = tmp_path / "checking.csv"
    _write_csv(p, ["Date", "Description", "Amount", "Balance"], [
        ["2026-03-01", "PAYROLL DEPOSIT", "3500.00", "3500.00"],
        ["2026-03-05", "WALMART", "-87.43", "3412.57"],
    ])
    stmt = parse_csv_statement(str(p))
    assert len(stmt.transactions) == 2
    assert stmt.transactions[0].amount == 3500.00
    assert stmt.transactions[1].amount == -87.43
    assert stmt.closing_balance == 3412.57
    assert stmt.account_name == "Checking"


def test_parse_separate_debit_credit_columns(tmp_path):
    p = tmp_path / "acct.csv"
    _write_csv(p, ["Date", "Description", "Debit", "Credit"], [
        ["03/01/2026", "Paycheck", "", "2000.00"],
        ["03/02/2026", "Groceries", "55.10", ""],
    ])
    stmt = parse_csv_statement(str(p))
    assert stmt.transactions[0].amount == 2000.00   # credit = positive
    assert stmt.transactions[1].amount == -55.10    # debit = negative


def test_parse_alternate_column_names(tmp_path):
    p = tmp_path / "acct.csv"
    _write_csv(p, ["Transaction Date", "Merchant", "Transaction Amount"], [
        ["2026-01-15", "Coffee Shop", "-4.50"],
    ])
    stmt = parse_csv_statement(str(p))
    assert len(stmt.transactions) == 1
    assert stmt.transactions[0].description == "Coffee Shop"


def test_credit_card_sign_normalization(tmp_path):
    """A CC export with charges as positive numbers should be flipped negative."""
    p = tmp_path / "visa.csv"
    _write_csv(p, ["Date", "Description", "Amount"], [
        ["2026-03-01", "AMAZON", "64.99"],     # charge exported positive
        ["2026-03-02", "TARGET", "120.00"],    # charge exported positive
        ["2026-03-15", "PAYMENT", "-100.00"],  # payment exported negative
    ])
    stmt = parse_csv_statement(str(p), is_credit_card=True)
    amounts = {t.description: t.amount for t in stmt.transactions}
    assert amounts["AMAZON"] == -64.99   # flipped to negative (money out)
    assert amounts["TARGET"] == -120.00
    assert amounts["PAYMENT"] == 100.00  # flipped to positive (money in)


def test_clean_float_handles_currency_and_parens():
    assert _clean_float("$1,234.56") == 1234.56
    assert _clean_float("(45.00)") == -45.00
    assert _clean_float("-7.25") == -7.25


def test_parse_date_formats():
    assert _parse_date("03/15/2026") == "2026-03-15"
    assert _parse_date("2026-03-15") == "2026-03-15"
    assert _parse_date("not a date") is None


def test_parse_amount_single_column():
    assert _parse_amount("-50.00", "", "") == -50.00
    assert _parse_amount("100.00", "", "") == 100.00


# ── Snapshot aggregation ───────────────────────────────────────────────────────

def _txn(date, desc, amount, cat, source="checking.csv", transfer=False):
    return Transaction(date=date, description=desc, amount=amount, source_file=source,
                       category=cat, is_transfer=transfer)


def test_snapshot_aggregates_income_and_expenses():
    txns = [
        _txn("2026-03-01", "Pay", 3000.0, TransactionCategory.INCOME),
        _txn("2026-03-05", "Rent", -1000.0, TransactionCategory.HOUSING),
        _txn("2026-03-10", "Food", -200.0, TransactionCategory.GROCERIES),
        _txn("2026-04-01", "Pay", 3000.0, TransactionCategory.INCOME),
        _txn("2026-04-05", "Rent", -1000.0, TransactionCategory.HOUSING),
    ]
    bank = BankAccount(account_name="Checking", current_balance=5000.0)
    snap = compute_financial_snapshot([bank], [], txns)
    assert len(snap.monthly_summaries) == 2
    # Avg income across 2 months = 3000
    assert snap.total_monthly_income == 3000.0
    assert snap.income_source == "historical"
    assert snap.total_liquid_assets == 5000.0


def test_snapshot_projected_income_overrides_historical():
    txns = [
        _txn("2026-03-01", "Pay", 2000.0, TransactionCategory.INCOME),
        _txn("2026-03-05", "Rent", -1000.0, TransactionCategory.HOUSING),
    ]
    snap = compute_financial_snapshot([], [], txns, projected_income=5000.0)
    assert snap.total_monthly_income == 5000.0
    assert snap.historical_monthly_income == 2000.0
    assert snap.income_source == "projected"
    assert snap.net_monthly_cash_flow == 5000.0 - 1000.0


def test_snapshot_excludes_transfers():
    txns = [
        _txn("2026-03-01", "Pay", 2000.0, TransactionCategory.INCOME),
        _txn("2026-03-10", "CC Payment", -500.0, TransactionCategory.DEBT_PAYMENT, transfer=True),
    ]
    snap = compute_financial_snapshot([], [], txns)
    # Transfer should not count as an expense
    assert snap.total_monthly_expenses == 0.0


# ── Debt payoff: the accounting identity ───────────────────────────────────────

def _interest_identity_holds(plan, cards):
    original = sum(c.current_balance for c in cards)
    total_paid = sum(m.payment_amount for m in plan.payoff_schedule)
    return abs((total_paid - original) - plan.total_interest_paid) < 0.05


@pytest.mark.parametrize("budget", [130.0, 355.29, 600.0, 10000.0])
def test_payoff_interest_identity(budget):
    """Total interest paid must equal total payments minus original principal."""
    cards = [
        CreditCardAccount(account_name="A", current_balance=800.0, annual_interest_rate=0.2699, minimum_payment=25.0),
        CreditCardAccount(account_name="B", current_balance=3200.0, annual_interest_rate=0.1899, minimum_payment=64.0),
        CreditCardAccount(account_name="C", current_balance=1500.0, annual_interest_rate=0.2399, minimum_payment=35.0),
    ]
    for fn in (compute_avalanche_plan, compute_snowball_plan):
        plan = fn([c.model_copy() for c in cards], budget)
        assert _interest_identity_holds(plan, cards), f"identity broken for budget={budget}"


def test_avalanche_targets_highest_apr_first():
    cards = [
        CreditCardAccount(account_name="LowAPR", current_balance=500.0, annual_interest_rate=0.12, minimum_payment=20.0),
        CreditCardAccount(account_name="HighAPR", current_balance=3000.0, annual_interest_rate=0.26, minimum_payment=60.0),
    ]
    plan = compute_avalanche_plan(cards, 400.0)
    assert plan.payoff_order[0] == "HighAPR"


def test_snowball_targets_smallest_balance_first():
    cards = [
        CreditCardAccount(account_name="Small", current_balance=500.0, annual_interest_rate=0.12, minimum_payment=20.0),
        CreditCardAccount(account_name="Big", current_balance=3000.0, annual_interest_rate=0.26, minimum_payment=60.0),
    ]
    plan = compute_snowball_plan(cards, 400.0)
    assert plan.payoff_order[0] == "Small"


def test_avalanche_costs_no_more_interest_than_snowball():
    """Avalanche is mathematically optimal for interest — never worse than snowball."""
    cards = [
        CreditCardAccount(account_name="Small", current_balance=500.0, annual_interest_rate=0.12, minimum_payment=20.0),
        CreditCardAccount(account_name="Big", current_balance=3000.0, annual_interest_rate=0.26, minimum_payment=60.0),
    ]
    av = compute_avalanche_plan([c.model_copy() for c in cards], 400.0)
    sn = compute_snowball_plan([c.model_copy() for c in cards], 400.0)
    assert av.total_interest_paid <= sn.total_interest_paid + 0.01


def test_payoff_eventually_clears_all_debt():
    cards = [CreditCardAccount(account_name="X", current_balance=1000.0,
                               annual_interest_rate=0.20, minimum_payment=50.0)]
    plan = compute_avalanche_plan(cards, 200.0)
    assert plan.payoff_order == ["X"]
    assert plan.payoff_schedule[-1].remaining_balance == 0.0


def test_default_budget_is_minimums_plus_surplus():
    cards = [
        CreditCardAccount(account_name="A", current_balance=1000.0, annual_interest_rate=0.20, minimum_payment=25.0),
        CreditCardAccount(account_name="B", current_balance=2000.0, annual_interest_rate=0.18, minimum_payment=50.0),
    ]
    # minimums = 75, net cash flow 1000 -> +30% = 300, total 375
    assert default_monthly_budget(cards, 1000.0) == 375.0
    # Negative cash flow contributes nothing extra
    assert default_monthly_budget(cards, -500.0) == 75.0


# ── Budget framework ──────────────────────────────────────────────────────────

def test_budget_5030_20_targets():
    txns = [
        _txn("2026-03-01", "Pay", 4000.0, TransactionCategory.INCOME),
        _txn("2026-03-05", "Rent", -1500.0, TransactionCategory.HOUSING),
        _txn("2026-03-10", "Dining", -300.0, TransactionCategory.DINING),
    ]
    snap = compute_financial_snapshot([], [], txns, projected_income=4000.0)
    bp = compute_budget_framework(snap)
    assert bp.needs_target == 2000.0
    assert bp.wants_target == 1200.0
    assert bp.savings_debt_target == 800.0
    # Housing is a need, dining is a want
    assert bp.current_needs == 1500.0
    assert bp.current_wants == 300.0


def test_budget_category_recommendations_sum_within_bucket():
    """Recommended amounts within a bucket should sum to that bucket's target."""
    txns = [
        _txn("2026-03-01", "Pay", 4000.0, TransactionCategory.INCOME),
        _txn("2026-03-05", "Rent", -1200.0, TransactionCategory.HOUSING),
        _txn("2026-03-06", "Power", -200.0, TransactionCategory.UTILITIES),
        _txn("2026-03-10", "Dining", -300.0, TransactionCategory.DINING),
        _txn("2026-03-12", "Movies", -100.0, TransactionCategory.ENTERTAINMENT),
    ]
    snap = compute_financial_snapshot([], [], txns, projected_income=4000.0)
    bp = compute_budget_framework(snap)
    needs_rec = sum(c.recommended_monthly for c in bp.category_budgets if c.bucket == "needs")
    wants_rec = sum(c.recommended_monthly for c in bp.category_budgets if c.bucket == "wants")
    assert needs_rec == pytest.approx(bp.needs_target, abs=0.05)
    assert wants_rec == pytest.approx(bp.wants_target, abs=0.05)
