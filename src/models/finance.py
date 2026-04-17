"""Pydantic models for the personal finance application."""

from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class TransactionCategory(str, Enum):
    INCOME = "income"
    HOUSING = "housing"
    GROCERIES = "groceries"
    DINING = "dining"
    UTILITIES = "utilities"
    TRANSPORT = "transport"
    ENTERTAINMENT = "entertainment"
    HEALTHCARE = "healthcare"
    CLOTHING = "clothing"
    DEBT_PAYMENT = "debt_payment"
    SAVINGS = "savings"
    SUBSCRIPTIONS = "subscriptions"
    OTHER = "other"


class AccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    LOAN = "loan"


class Transaction(BaseModel):
    date: str  # ISO format YYYY-MM-DD
    description: str
    amount: float  # negative = debit, positive = credit/income
    balance: float | None = None
    source_file: str
    category: TransactionCategory | None = None
    is_transfer: bool = False


class RawStatement(BaseModel):
    file_path: str
    account_name: str
    transactions: list[Transaction]
    opening_balance: float | None = None
    closing_balance: float | None = None


class CreditCardAccount(BaseModel):
    account_name: str
    current_balance: float  # amount owed (positive = debt)
    annual_interest_rate: float  # decimal e.g. 0.2199 for 21.99%
    minimum_payment: float
    credit_limit: float | None = None
    transactions: list[Transaction] = Field(default_factory=list)


class BankAccount(BaseModel):
    account_name: str
    current_balance: float
    account_type: AccountType = AccountType.CHECKING
    transactions: list[Transaction] = Field(default_factory=list)


class SpendingByCategory(BaseModel):
    category: TransactionCategory
    total_amount: float
    transaction_count: int
    percentage_of_spending: float
    monthly_average: float


class MonthlySpendingSummary(BaseModel):
    month: str  # "YYYY-MM"
    total_income: float
    total_expenses: float
    net_cash_flow: float
    by_category: list[SpendingByCategory] = Field(default_factory=list)


class FinancialSnapshot(BaseModel):
    total_liquid_assets: float
    total_credit_card_debt: float
    total_monthly_income: float
    total_monthly_expenses: float
    net_monthly_cash_flow: float
    monthly_summaries: list[MonthlySpendingSummary] = Field(default_factory=list)
    bank_accounts: list[BankAccount] = Field(default_factory=list)
    credit_cards: list[CreditCardAccount] = Field(default_factory=list)
    analysis_period_start: str
    analysis_period_end: str
    spending_by_category: list[SpendingByCategory] = Field(default_factory=list)


class DebtPayoffMonth(BaseModel):
    month_number: int
    account_name: str
    payment_amount: float
    principal_paid: float
    interest_paid: float
    remaining_balance: float


class DebtPayoffPlan(BaseModel):
    strategy: str  # "avalanche" or "snowball"
    monthly_payment_budget: float
    total_months: int
    total_interest_paid: float
    payoff_schedule: list[DebtPayoffMonth] = Field(default_factory=list)
    payoff_order: list[str] = Field(default_factory=list)


class BudgetCategory(BaseModel):
    category: TransactionCategory
    bucket: str  # "needs", "wants", "savings_debt"
    current_monthly_avg: float
    recommended_monthly: float
    difference: float  # recommended - current; negative = overspending


class BudgetPlan(BaseModel):
    framework: str  # "50/30/20"
    monthly_income: float
    needs_target: float
    wants_target: float
    savings_debt_target: float
    current_needs: float
    current_wants: float
    current_savings_debt: float
    category_budgets: list[BudgetCategory] = Field(default_factory=list)
    surplus_or_deficit: float  # positive = surplus, negative = deficit


class MonthlyActionPlan(BaseModel):
    month: str  # "May 2026"
    priority_actions: list[str] = Field(default_factory=list)
    debt_payments: dict[str, float] = Field(default_factory=dict)
    savings_target: float
    budget_targets: dict[str, float] = Field(default_factory=dict)
    key_milestones: list[str] = Field(default_factory=list)


class FinancialReport(BaseModel):
    snapshot: FinancialSnapshot
    categorized_transactions: list[Transaction] = Field(default_factory=list)
    avalanche_plan: DebtPayoffPlan | None = None
    snowball_plan: DebtPayoffPlan | None = None
    budget_plan: BudgetPlan | None = None
    monthly_action_plans: list[MonthlyActionPlan] = Field(default_factory=list)
    executive_summary: str = ""
    top_recommendations: list[str] = Field(default_factory=list)
    output_dir: str = ""
    generated_at: str = ""
