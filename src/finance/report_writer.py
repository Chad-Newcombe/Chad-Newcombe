"""Generate a human-readable markdown finance report."""

from __future__ import annotations
from pathlib import Path

from src.models.finance import DebtPayoffPlan, FinancialReport


def write_markdown_report(report: FinancialReport, output_dir: Path) -> Path:
    """Write finance_report.md to output_dir and return the path."""
    lines: list[str] = []

    snap = report.snapshot
    period = f"{snap.analysis_period_start} to {snap.analysis_period_end}"

    lines += [
        f"# Personal Finance Analysis — {period}",
        "",
    ]

    # Executive Summary
    if report.executive_summary:
        lines += ["## Executive Summary", "", report.executive_summary, ""]

    # Financial Snapshot
    income_label = (
        "Projected Monthly Income"
        if snap.income_source == "projected"
        else "Avg Monthly Income (historical)"
    )
    income_note = (
        f" *(historical avg: ${snap.historical_monthly_income:,.2f})*"
        if snap.income_source == "projected"
        else ""
    )
    lines += [
        "## Financial Snapshot",
        "",
        "| Metric | Amount |",
        "|--------|--------|",
        f"| Liquid Assets (Bank) | ${snap.total_liquid_assets:,.2f} |",
        f"| Total Credit Card Debt | ${snap.total_credit_card_debt:,.2f} |",
        f"| {income_label} | ${snap.total_monthly_income:,.2f}{income_note} |",
        f"| Avg Monthly Expenses | ${snap.total_monthly_expenses:,.2f} |",
        f"| Net Monthly Cash Flow | ${snap.net_monthly_cash_flow:,.2f} |",
        "",
    ]

    # Credit Cards
    if snap.credit_cards:
        lines += ["### Credit Card Balances", "", "| Account | Balance | APR | Min Payment |", "|---------|---------|-----|-------------|"]
        for cc in snap.credit_cards:
            lines.append(
                f"| {cc.account_name} | ${cc.current_balance:,.2f} | {cc.annual_interest_rate*100:.2f}% | ${cc.minimum_payment:,.2f} |"
            )
        lines.append("")

    # Spending by Category
    if snap.spending_by_category:
        lines += [
            "## Spending by Category (Monthly Average)",
            "",
            "| Category | Monthly Avg | % of Spending |",
            "|----------|-------------|---------------|",
        ]
        for cat in snap.spending_by_category:
            lines.append(f"| {cat.category.value.replace('_', ' ').title()} | ${cat.monthly_average:,.2f} | {cat.percentage_of_spending:.1f}% |")
        lines.append("")

    # Debt Payoff Comparison
    if report.avalanche_plan or report.snowball_plan:
        lines += ["## Debt Payoff Comparison", ""]
        av = report.avalanche_plan
        sn = report.snowball_plan
        lines += [
            "| Strategy | Months to Payoff | Total Interest Paid | Order |",
            "|----------|-----------------|---------------------|-------|",
        ]
        if av:
            order = " → ".join(av.payoff_order)
            lines.append(f"| Avalanche (highest APR first) | {av.total_months} | ${av.total_interest_paid:,.2f} | {order} |")
        if sn:
            order = " → ".join(sn.payoff_order)
            lines.append(f"| Snowball (smallest balance first) | {sn.total_months} | ${sn.total_interest_paid:,.2f} | {order} |")
        lines.append("")

        # Show 12-month schedule for the recommended (avalanche) strategy
        best = av or sn
        if best:
            lines += [
                f"### 12-Month Payment Schedule ({best.strategy.title()} Strategy)",
                "",
            ]
            _append_schedule_table(lines, best, max_months=12)
            lines.append("")

    # Budget Plan
    if report.budget_plan:
        bp = report.budget_plan
        lines += [
            f"## Budget Plan — {bp.framework} Analysis",
            "",
            f"Monthly Income: **${bp.monthly_income:,.2f}**",
            "",
            "| Bucket | Target | Current | Status |",
            "|--------|--------|---------|--------|",
        ]

        def _status(current: float, target: float) -> str:
            if current <= target:
                return "✓ On track"
            pct = (current - target) / target * 100
            return f"↑ Over by {pct:.0f}%"

        lines += [
            f"| Needs (50%) | ${bp.needs_target:,.2f} | ${bp.current_needs:,.2f} | {_status(bp.current_needs, bp.needs_target)} |",
            f"| Wants (30%) | ${bp.wants_target:,.2f} | ${bp.current_wants:,.2f} | {_status(bp.current_wants, bp.wants_target)} |",
            f"| Savings/Debt (20%) | ${bp.savings_debt_target:,.2f} | ${bp.current_savings_debt:,.2f} | {_status(bp.current_savings_debt, bp.savings_debt_target)} |",
            "",
            "### Category Budgets",
            "",
            "| Category | Current | Recommended | Difference |",
            "|----------|---------|-------------|------------|",
        ]
        for cb in sorted(bp.category_budgets, key=lambda x: x.current_monthly_avg, reverse=True):
            diff_str = f"+${cb.difference:,.2f}" if cb.difference >= 0 else f"-${abs(cb.difference):,.2f}"
            lines.append(
                f"| {cb.category.value.replace('_', ' ').title()} | ${cb.current_monthly_avg:,.2f} | ${cb.recommended_monthly:,.2f} | {diff_str} |"
            )
        lines.append("")

    # Monthly Action Plans
    if report.monthly_action_plans:
        lines += ["## Monthly Action Plans", ""]
        for plan in report.monthly_action_plans:
            lines += [f"### {plan.month}", ""]
            if plan.priority_actions:
                lines.append("**Priority Actions:**")
                for action in plan.priority_actions:
                    lines.append(f"- {action}")
                lines.append("")
            if plan.debt_payments:
                lines.append("**Debt Payments:**")
                for account, amount in plan.debt_payments.items():
                    lines.append(f"- {account}: ${amount:,.2f}")
                lines.append("")
            if plan.savings_target > 0:
                lines.append(f"**Savings Target:** ${plan.savings_target:,.2f}")
                lines.append("")
            if plan.key_milestones:
                lines.append("**Key Milestones:**")
                for milestone in plan.key_milestones:
                    lines.append(f"- {milestone}")
                lines.append("")

    # Top Recommendations
    if report.top_recommendations:
        lines += ["## Top Recommendations", ""]
        for i, rec in enumerate(report.top_recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    out_path = output_dir / "finance_report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _append_schedule_table(lines: list[str], plan: DebtPayoffPlan, max_months: int) -> None:
    """Append a month-by-month summary table (one row per month across all cards)."""
    from collections import defaultdict

    by_month: dict[int, dict] = defaultdict(lambda: {"payments": {}, "interest": 0.0})
    for entry in plan.payoff_schedule:
        if entry.month_number > max_months:
            continue
        by_month[entry.month_number]["payments"][entry.account_name] = entry.payment_amount
        by_month[entry.month_number]["interest"] += entry.interest_paid

    if not by_month:
        return

    lines += ["| Month | Total Payment | Interest Paid | Notes |", "|-------|---------------|---------------|-------|"]
    for month_num in sorted(by_month.keys()):
        data = by_month[month_num]
        total = sum(data["payments"].values())
        interest = data["interest"]
        notes = ", ".join(f"{acct}: ${amt:,.2f}" for acct, amt in data["payments"].items())
        lines.append(f"| {month_num} | ${total:,.2f} | ${interest:,.2f} | {notes} |")
