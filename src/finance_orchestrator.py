"""Finance pipeline orchestrator: CSV → categorize → analyze → plan → report."""

from __future__ import annotations
import json
from datetime import date
from pathlib import Path

import anthropic
from rich.console import Console
from rich.text import Text

from src import config
from src.agents.categorization_agent import CategorizationAgent
from src.agents.planning_agent import PlanningAgent
from src.finance.analyzer import (
    compute_avalanche_plan,
    compute_budget_framework,
    compute_financial_snapshot,
    compute_snowball_plan,
    default_monthly_budget,
)
from src.finance.parser import parse_csv_statement
from src.finance.report_writer import write_markdown_report
from src.models.finance import (
    BankAccount,
    CreditCardAccount,
    FinancialReport,
    RawStatement,
    Transaction,
)

console = Console()


class FinanceOrchestrator:
    def __init__(self, api_key: str | None = None) -> None:
        self.client = anthropic.Anthropic(api_key=api_key or config.ANTHROPIC_API_KEY)
        self.categorization_agent = CategorizationAgent(self.client, agent_label="categorizer")
        self.planning_agent = PlanningAgent(self.client, agent_label="planner")

    def analyze(
        self,
        statement_files: list[str],
        credit_card_configs: list[dict] | None = None,
        monthly_payment_budget: float | None = None,
    ) -> FinancialReport:
        """Run the full personal finance analysis pipeline."""
        credit_card_configs = credit_card_configs or []

        # ── Step 1: Parse CSVs ────────────────────────────────────────────────
        self._log_step("Parsing statements")
        statements: list[RawStatement] = []
        for f in statement_files:
            try:
                stmt = parse_csv_statement(f)
                statements.append(stmt)
                console.print(f"  [dim]Loaded {len(stmt.transactions)} transactions from {stmt.account_name}[/dim]")
            except Exception as exc:
                console.print(f"  [yellow]Warning:[/yellow] Could not parse {f}: {exc}")

        if not statements:
            raise ValueError("No valid CSV statements could be parsed.")

        # ── Step 2: Build account objects ────────────────────────────────────
        self._log_step("Building account profiles")
        cc_config_map = {cfg["name"].lower(): cfg for cfg in credit_card_configs}

        bank_accounts: list[BankAccount] = []
        credit_cards: list[CreditCardAccount] = []
        all_transactions: list[Transaction] = []

        for stmt in statements:
            all_transactions.extend(stmt.transactions)
            name_lower = stmt.account_name.lower()

            # Match to a credit card config by name similarity
            matched_cc = None
            for cc_name, cfg in cc_config_map.items():
                if cc_name in name_lower or name_lower in cc_name:
                    matched_cc = cfg
                    break

            if matched_cc:
                balance = matched_cc.get("balance") or (
                    abs(stmt.closing_balance) if stmt.closing_balance is not None else 0.0
                )
                credit_cards.append(CreditCardAccount(
                    account_name=stmt.account_name,
                    current_balance=float(balance),
                    annual_interest_rate=float(matched_cc["apr"]) / 100,
                    minimum_payment=float(matched_cc["min_payment"]),
                    credit_limit=float(matched_cc["credit_limit"]) if matched_cc.get("credit_limit") else None,
                    transactions=stmt.transactions,
                ))
            else:
                bank_balance = stmt.closing_balance if stmt.closing_balance is not None else 0.0
                bank_accounts.append(BankAccount(
                    account_name=stmt.account_name,
                    current_balance=float(bank_balance),
                    transactions=stmt.transactions,
                ))

        # Any credit card configs not matched to a statement (user provided config only)
        for cfg in credit_card_configs:
            already_added = any(cc.account_name.lower() == cfg["name"].lower() for cc in credit_cards)
            if not already_added:
                credit_cards.append(CreditCardAccount(
                    account_name=cfg["name"],
                    current_balance=float(cfg.get("balance", 0.0)),
                    annual_interest_rate=float(cfg["apr"]) / 100,
                    minimum_payment=float(cfg["min_payment"]),
                    credit_limit=float(cfg["credit_limit"]) if cfg.get("credit_limit") else None,
                ))

        # ── Step 3: AI categorization ─────────────────────────────────────────
        self._log_step(f"Categorizing {len(all_transactions)} transactions with AI")
        all_transactions = self.categorization_agent.run_categorization(all_transactions)

        # Push categorized transactions back into account objects
        txn_by_source: dict[str, list[Transaction]] = {}
        for t in all_transactions:
            txn_by_source.setdefault(t.source_file, []).append(t)
        for ba in bank_accounts:
            ba.transactions = txn_by_source.get(ba.transactions[0].source_file if ba.transactions else "", [])
        for cc in credit_cards:
            cc.transactions = txn_by_source.get(cc.transactions[0].source_file if cc.transactions else "", [])

        # ── Step 4: Compute financial snapshot ───────────────────────────────
        self._log_step("Computing financial snapshot")
        snapshot = compute_financial_snapshot(bank_accounts, credit_cards, all_transactions)

        # ── Step 5: Debt payoff plans ─────────────────────────────────────────
        avalanche_plan = None
        snowball_plan = None
        if credit_cards:
            self._log_step("Computing debt payoff plans")
            budget = monthly_payment_budget or default_monthly_budget(
                credit_cards, snapshot.net_monthly_cash_flow
            )
            avalanche_plan = compute_avalanche_plan(credit_cards, budget)
            snowball_plan = compute_snowball_plan(credit_cards, budget)
            console.print(
                f"  [dim]Avalanche: {avalanche_plan.total_months} months, "
                f"${avalanche_plan.total_interest_paid:,.2f} interest | "
                f"Snowball: {snowball_plan.total_months} months, "
                f"${snowball_plan.total_interest_paid:,.2f} interest[/dim]"
            )

        # ── Step 6: Budget framework ──────────────────────────────────────────
        self._log_step("Analyzing budget (50/30/20)")
        budget_plan = compute_budget_framework(snapshot)

        # ── Step 7: AI planning ───────────────────────────────────────────────
        self._log_step("Generating financial plan with AI")
        executive_summary, recommendations, monthly_plans = self.planning_agent.run_planning(
            snapshot, avalanche_plan, snowball_plan, budget_plan
        )

        # ── Step 8: Build report and save ─────────────────────────────────────
        output_dir = self._make_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        report = FinancialReport(
            snapshot=snapshot,
            categorized_transactions=all_transactions,
            avalanche_plan=avalanche_plan,
            snowball_plan=snowball_plan,
            budget_plan=budget_plan,
            monthly_action_plans=monthly_plans,
            executive_summary=executive_summary,
            top_recommendations=recommendations,
            output_dir=str(output_dir),
            generated_at=date.today().isoformat(),
        )

        self._save_outputs(report, output_dir)

        console.print(f"\n[green]✓[/green] Report saved to [cyan]{output_dir}[/cyan]")
        return report

    # ── Private helpers ───────────────────────────────────────────────────────

    def _log_step(self, message: str) -> None:
        t = Text()
        t.append("  ▶ ", style="bold green")
        t.append(message, style="white")
        console.print(t)

    def _make_output_dir(self) -> Path:
        base = Path(config.OUTPUT_DIR)
        slug = f"finance-{date.today().isoformat()}"
        return base / slug

    def _save_outputs(self, report: FinancialReport, output_dir: Path) -> None:
        (output_dir / "report.json").write_text(
            report.model_dump_json(indent=2), encoding="utf-8"
        )
        (output_dir / "transactions.json").write_text(
            json.dumps([t.model_dump() for t in report.categorized_transactions], indent=2),
            encoding="utf-8",
        )

        payoff_data: dict = {}
        if report.avalanche_plan:
            payoff_data["avalanche"] = report.avalanche_plan.model_dump()
        if report.snowball_plan:
            payoff_data["snowball"] = report.snowball_plan.model_dump()
        if payoff_data:
            (output_dir / "debt_payoff.json").write_text(
                json.dumps(payoff_data, indent=2), encoding="utf-8"
            )

        if report.budget_plan:
            (output_dir / "budget.json").write_text(
                report.budget_plan.model_dump_json(indent=2), encoding="utf-8"
            )

        write_markdown_report(report, output_dir)
