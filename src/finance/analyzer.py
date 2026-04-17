"""Pure-Python financial analysis: spending aggregation, debt payoff, budget framework."""

from __future__ import annotations
import copy
from collections import defaultdict

from src.models.finance import (
    BankAccount,
    BudgetCategory,
    BudgetPlan,
    CreditCardAccount,
    DebtPayoffMonth,
    DebtPayoffPlan,
    FinancialSnapshot,
    MonthlySpendingSummary,
    SpendingByCategory,
    Transaction,
    TransactionCategory,
)

_NEEDS_CATEGORIES = {
    TransactionCategory.HOUSING,
    TransactionCategory.GROCERIES,
    TransactionCategory.UTILITIES,
    TransactionCategory.TRANSPORT,
    TransactionCategory.HEALTHCARE,
    TransactionCategory.DEBT_PAYMENT,
}

_WANTS_CATEGORIES = {
    TransactionCategory.DINING,
    TransactionCategory.ENTERTAINMENT,
    TransactionCategory.CLOTHING,
    TransactionCategory.SUBSCRIPTIONS,
    TransactionCategory.OTHER,
}

_SAVINGS_DEBT_CATEGORIES = {
    TransactionCategory.SAVINGS,
    TransactionCategory.DEBT_PAYMENT,
}


def compute_financial_snapshot(
    bank_accounts: list[BankAccount],
    credit_cards: list[CreditCardAccount],
    transactions: list[Transaction],
    projected_income: float | None = None,
) -> FinancialSnapshot:
    """Aggregate transactions into a FinancialSnapshot.

    If projected_income is given it overrides the historical average for all
    forward-looking calculations (budgets, payoff plans, monthly action plans).
    The historical average is always preserved for reference.
    """
    if not transactions:
        dates = ["0000-01", "0000-01"]
    else:
        sorted_dates = sorted(t.date for t in transactions)
        dates = [sorted_dates[0], sorted_dates[-1]]

    monthly: dict[str, list[Transaction]] = defaultdict(list)
    for t in transactions:
        if not t.is_transfer:
            monthly[t.date[:7]].append(t)

    monthly_summaries: list[MonthlySpendingSummary] = []
    for month in sorted(monthly.keys()):
        txns = monthly[month]
        income = sum(t.amount for t in txns if t.amount > 0)
        expenses = sum(abs(t.amount) for t in txns if t.amount < 0)
        summary = MonthlySpendingSummary(
            month=month,
            total_income=round(income, 2),
            total_expenses=round(expenses, 2),
            net_cash_flow=round(income - expenses, 2),
            by_category=_group_by_category(txns, expenses),
        )
        monthly_summaries.append(summary)

    num_months = max(len(monthly_summaries), 1)
    historical_avg_income = sum(s.total_income for s in monthly_summaries) / num_months
    avg_expenses = sum(s.total_expenses for s in monthly_summaries) / num_months

    effective_income = projected_income if projected_income is not None else historical_avg_income
    income_source = "projected" if projected_income is not None else "historical"

    all_expenses = sum(abs(t.amount) for t in transactions if t.amount < 0 and not t.is_transfer)
    spending_by_cat = _group_by_category(
        [t for t in transactions if t.amount < 0 and not t.is_transfer],
        all_expenses,
        monthly_divisor=num_months,
    )

    return FinancialSnapshot(
        total_liquid_assets=round(sum(b.current_balance for b in bank_accounts), 2),
        total_credit_card_debt=round(sum(c.current_balance for c in credit_cards), 2),
        total_monthly_income=round(effective_income, 2),
        historical_monthly_income=round(historical_avg_income, 2),
        income_source=income_source,
        total_monthly_expenses=round(avg_expenses, 2),
        net_monthly_cash_flow=round(effective_income - avg_expenses, 2),
        monthly_summaries=monthly_summaries,
        bank_accounts=bank_accounts,
        credit_cards=credit_cards,
        analysis_period_start=dates[0],
        analysis_period_end=dates[-1],
        spending_by_category=spending_by_cat,
    )


def _group_by_category(
    transactions: list[Transaction],
    total_expenses: float,
    monthly_divisor: int = 1,
) -> list[SpendingByCategory]:
    """Aggregate transactions by category into SpendingByCategory list."""
    buckets: dict[TransactionCategory, list[Transaction]] = defaultdict(list)
    for t in transactions:
        cat = t.category or TransactionCategory.OTHER
        buckets[cat].append(t)

    result = []
    for cat, txns in buckets.items():
        total = sum(abs(t.amount) for t in txns)
        pct = (total / total_expenses * 100) if total_expenses > 0 else 0.0
        result.append(
            SpendingByCategory(
                category=cat,
                total_amount=round(total, 2),
                transaction_count=len(txns),
                percentage_of_spending=round(pct, 1),
                monthly_average=round(total / monthly_divisor, 2),
            )
        )
    return sorted(result, key=lambda x: x.total_amount, reverse=True)


def compute_avalanche_plan(
    credit_cards: list[CreditCardAccount],
    monthly_budget: float,
) -> DebtPayoffPlan:
    """Pay minimums on all cards; surplus goes to the highest-APR card first."""
    return _simulate_payoff(credit_cards, monthly_budget, "avalanche")


def compute_snowball_plan(
    credit_cards: list[CreditCardAccount],
    monthly_budget: float,
) -> DebtPayoffPlan:
    """Pay minimums on all cards; surplus goes to the smallest-balance card first."""
    return _simulate_payoff(credit_cards, monthly_budget, "snowball")


def _simulate_payoff(
    cards: list[CreditCardAccount],
    monthly_budget: float,
    strategy: str,
) -> DebtPayoffPlan:
    """Shared simulation loop for avalanche and snowball strategies."""

    class CardState:
        def __init__(self, card: CreditCardAccount) -> None:
            self.name = card.account_name
            self.balance = card.current_balance
            self.monthly_rate = card.annual_interest_rate / 12
            self.min_payment = card.minimum_payment
            self.apr = card.annual_interest_rate

    states = [CardState(c) for c in cards if c.current_balance > 0]

    def sort_key(s: CardState) -> float:
        return -s.apr if strategy == "avalanche" else s.balance

    states.sort(key=sort_key)

    schedule: list[DebtPayoffMonth] = []
    payoff_order: list[str] = []
    total_interest = 0.0
    month = 0

    while any(s.balance > 0.001 for s in states) and month < 360:
        month += 1
        remaining_budget = monthly_budget

        # Accrue interest
        for s in states:
            if s.balance > 0.001:
                s.balance += s.balance * s.monthly_rate

        # Pay minimums on all active cards
        for s in states:
            if s.balance <= 0.001:
                continue
            payment = min(s.min_payment, s.balance)
            interest = s.balance * s.monthly_rate / (1 + s.monthly_rate)  # approx
            interest = min(interest, payment)
            principal = payment - interest
            s.balance -= payment
            remaining_budget -= payment
            total_interest += interest
            schedule.append(DebtPayoffMonth(
                month_number=month,
                account_name=s.name,
                payment_amount=round(payment, 2),
                principal_paid=round(principal, 2),
                interest_paid=round(interest, 2),
                remaining_balance=round(max(s.balance, 0.0), 2),
            ))
            if s.balance < 0.001:
                s.balance = 0.0
                if s.name not in payoff_order:
                    payoff_order.append(s.name)
                remaining_budget += s.min_payment  # freed minimum rolls into surplus

        # Apply surplus to priority card
        if remaining_budget > 0.001:
            active = [s for s in states if s.balance > 0.001]
            active.sort(key=sort_key)
            if active:
                target = active[0]
                extra = min(remaining_budget, target.balance)
                target.balance -= extra
                # Update last schedule entry for this card this month
                for entry in reversed(schedule):
                    if entry.month_number == month and entry.account_name == target.name:
                        entry.payment_amount = round(entry.payment_amount + extra, 2)
                        entry.principal_paid = round(entry.principal_paid + extra, 2)
                        entry.remaining_balance = round(max(target.balance, 0.0), 2)
                        break
                if target.balance < 0.001:
                    target.balance = 0.0
                    if target.name not in payoff_order:
                        payoff_order.append(target.name)

    # Any cards still not in payoff_order (edge case — never paid off)
    for s in states:
        if s.name not in payoff_order:
            payoff_order.append(s.name)

    return DebtPayoffPlan(
        strategy=strategy,
        monthly_payment_budget=round(monthly_budget, 2),
        total_months=month,
        total_interest_paid=round(total_interest, 2),
        payoff_schedule=schedule,
        payoff_order=payoff_order,
    )


def default_monthly_budget(
    credit_cards: list[CreditCardAccount],
    net_monthly_cash_flow: float,
) -> float:
    """If user doesn't specify a budget, use minimums + 30% of surplus cash flow."""
    total_minimums = sum(c.minimum_payment for c in credit_cards)
    surplus_contribution = max(0.0, net_monthly_cash_flow * 0.3)
    return round(total_minimums + surplus_contribution, 2)


def compute_budget_framework(
    snapshot: FinancialSnapshot,
    framework: str = "50/30/20",
) -> BudgetPlan:
    """Build a 50/30/20 budget plan comparing current spending to targets.

    Uses snapshot.total_monthly_income which is projected income when provided,
    giving accurate forward-looking budget targets.
    """
    income = snapshot.total_monthly_income
    if income <= 0:
        income = 1.0  # avoid division by zero

    needs_target = income * 0.50
    wants_target = income * 0.30
    savings_debt_target = income * 0.20

    # Pre-compute bucket totals before assigning proportions (avoids running-total bug)
    needs_total = sum(
        s.monthly_average for s in snapshot.spending_by_category
        if s.category in _NEEDS_CATEGORIES and s.category != TransactionCategory.DEBT_PAYMENT
    )
    savings_debt_total = sum(
        s.monthly_average for s in snapshot.spending_by_category
        if s.category in _SAVINGS_DEBT_CATEGORIES
    )
    wants_total = sum(
        s.monthly_average for s in snapshot.spending_by_category
        if s.category not in _NEEDS_CATEGORIES and s.category not in _SAVINGS_DEBT_CATEGORIES
    )

    category_budgets: list[BudgetCategory] = []

    for cat_summary in snapshot.spending_by_category:
        cat = cat_summary.category
        avg = cat_summary.monthly_average

        if cat in _NEEDS_CATEGORIES and cat != TransactionCategory.DEBT_PAYMENT:
            bucket = "needs"
            bucket_total = needs_total
            bucket_target = needs_target
        elif cat in _SAVINGS_DEBT_CATEGORIES:
            bucket = "savings_debt"
            bucket_total = savings_debt_total
            bucket_target = savings_debt_target
        else:
            bucket = "wants"
            bucket_total = wants_total
            bucket_target = wants_target

        recommended = bucket_target * (avg / max(bucket_total, 0.01))

        category_budgets.append(BudgetCategory(
            category=cat,
            bucket=bucket,
            current_monthly_avg=round(avg, 2),
            recommended_monthly=round(recommended, 2),
            difference=round(recommended - avg, 2),
        ))

    current_needs = needs_total
    current_wants = wants_total
    current_savings_debt = savings_debt_total
    surplus = income - current_needs - current_wants - current_savings_debt

    return BudgetPlan(
        framework=framework,
        monthly_income=round(income, 2),
        needs_target=round(needs_target, 2),
        wants_target=round(wants_target, 2),
        savings_debt_target=round(savings_debt_target, 2),
        current_needs=round(current_needs, 2),
        current_wants=round(current_wants, 2),
        current_savings_debt=round(current_savings_debt, 2),
        category_budgets=category_budgets,
        surplus_or_deficit=round(surplus, 2),
    )
