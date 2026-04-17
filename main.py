#!/usr/bin/env python3
"""
Digital Product Agents — CLI entry point.

Usage:
    python main.py create "productivity system for solopreneurs" --type ebook
    python main.py create "Notion CRM template" --type template
    python main.py create "30-day social media planner" --type planner
"""

from __future__ import annotations
from pathlib import Path
from typing import Annotated
import typer
from rich.console import Console
from rich.text import Text

app = typer.Typer(
    name="dp",
    help="AI agents that research, create, design, list, and market digital products.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

PRODUCT_TYPES = ["ebook", "template", "workbook", "checklist", "guide", "course", "planner"]


@app.command()
def create(
    idea: Annotated[str, typer.Argument(help="Your product idea in plain English.")],
    product_type: Annotated[
        str,
        typer.Option(
            "--type", "-t",
            help=f"Product type. One of: {', '.join(PRODUCT_TYPES)}",
        ),
    ] = "ebook",
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", "-k", help="Anthropic API key (or set ANTHROPIC_API_KEY env var).", envvar="ANTHROPIC_API_KEY"),
    ] = None,
) -> None:
    """
    Run the full 5-agent pipeline to create a complete digital product package.

    Each run produces:

    \b
    outputs/<slug>/
    ├── content.md          — the product content
    ├── research.json       — market research
    ├── product_page.html   — ready-to-publish landing page
    ├── listings/
    │   ├── etsy.json
    │   ├── gumroad.json
    │   └── payhip.json
    └── marketing/
        ├── social_posts.json
        ├── email_sequence.json
        ├── ad_copy.json
        ├── pinterest_pins.json
        └── content_calendar.json
    """
    if product_type not in PRODUCT_TYPES:
        console.print(f"[red]Unknown product type '{product_type}'. Choose from: {', '.join(PRODUCT_TYPES)}[/red]")
        raise typer.Exit(code=1)

    from src.orchestrator import Orchestrator

    try:
        orchestrator = Orchestrator(api_key=api_key)
        orchestrator.create_product(idea, product_type)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
    except Exception as exc:
        console.print(f"\n[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command()
def analyze(
    statements: Annotated[
        list[Path],
        typer.Argument(help="CSV statement files exported from your bank or credit card."),
    ],
    credit_card: Annotated[
        list[str] | None,
        typer.Option(
            "--cc", "-c",
            help=(
                'Credit card config as "name:APR:min_payment" or '
                '"name:APR:min_payment:balance" e.g. "Visa:21.99:25:2400"'
            ),
        ),
    ] = None,
    monthly_budget: Annotated[
        float | None,
        typer.Option(
            "--budget", "-b",
            help="Total monthly dollars available for debt repayment. Auto-calculated if omitted.",
        ),
    ] = None,
    income: Annotated[
        float | None,
        typer.Option(
            "--income", "-i",
            help=(
                "Your projected monthly take-home income. "
                "If omitted, the historical average from your statements is used. "
                "Use this when your income has recently changed or statements don't "
                "reflect your current pay (e.g. new job, raise, side income)."
            ),
        ),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", "-k", help="Anthropic API key.", envvar="ANTHROPIC_API_KEY"),
    ] = None,
) -> None:
    """
    Analyze bank and credit card statements to produce a personal finance plan.

    \b
    Example:
        python main.py analyze checking.csv visa.csv amex.csv \\
            --cc "Visa:21.99:25" --cc "Amex:18.99:35:3200" \\
            --income 4500 --budget 600

    \b
    Outputs saved to outputs/finance-YYYY-MM-DD/:
        finance_report.md  — human-readable summary
        report.json        — complete structured data
        transactions.json  — categorized transactions
        debt_payoff.json   — avalanche + snowball schedules
        budget.json        — 50/30/20 budget plan
    """
    # Validate statement files
    for path in statements:
        if not path.exists():
            console.print(f"[red]File not found:[/red] {path}")
            raise typer.Exit(code=1)

    # Parse credit card configs from "name:APR:min_payment[:balance[:limit]]"
    cc_configs: list[dict] = []
    for cc_str in (credit_card or []):
        parts = cc_str.split(":")
        if len(parts) < 3:
            console.print(f"[red]Invalid --cc format:[/red] {cc_str!r}  (expected name:APR:min_payment)")
            raise typer.Exit(code=1)
        cfg: dict = {
            "name": parts[0].strip(),
            "apr": float(parts[1]),
            "min_payment": float(parts[2]),
        }
        if len(parts) >= 4:
            cfg["balance"] = float(parts[3])
        if len(parts) >= 5:
            cfg["credit_limit"] = float(parts[4])
        cc_configs.append(cfg)

    from src.finance_orchestrator import FinanceOrchestrator

    console.print("\n[bold cyan]Personal Finance Analyzer[/bold cyan]")
    console.print(f"  Statements: {', '.join(str(s) for s in statements)}")
    if cc_configs:
        console.print(f"  Credit cards: {', '.join(c['name'] for c in cc_configs)}")
    if income:
        console.print(f"  Projected income: ${income:,.2f}/mo")
    else:
        console.print("  Income: using historical average from statements")
    if monthly_budget:
        console.print(f"  Monthly debt budget: ${monthly_budget:,.2f}")
    console.print()

    try:
        orchestrator = FinanceOrchestrator(api_key=api_key)
        orchestrator.analyze(
            statement_files=[str(s) for s in statements],
            credit_card_configs=cc_configs,
            monthly_payment_budget=monthly_budget,
            projected_income=income,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
    except Exception as exc:
        console.print(f"\n[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command()
def types() -> None:
    """List all supported product types."""
    from rich.table import Table
    from rich import box

    table = Table(title="Supported Product Types", box=box.SIMPLE_HEAD)
    table.add_column("Type", style="cyan bold")
    table.add_column("Description")

    descriptions = {
        "ebook": "Comprehensive e-book or ultimate guide (5-8 chapters)",
        "template": "Plug-and-play template with usage instructions",
        "workbook": "Interactive workbook with exercises and prompts",
        "checklist": "Detailed checklist broken into phases",
        "guide": "Practical how-to guide with step-by-step instructions",
        "course": "Mini-course with modules, lessons, and assignments",
        "planner": "Structured planner with framework and templates",
    }

    for t, desc in descriptions.items():
        table.add_row(t, desc)

    console.print(table)


if __name__ == "__main__":
    app()
