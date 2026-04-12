#!/usr/bin/env python3
"""
Digital Product Agents — CLI entry point.

Usage:
    python main.py create "productivity system for solopreneurs" --type ebook
    python main.py create "Notion CRM template" --type template
    python main.py create "30-day social media planner" --type planner
"""

from __future__ import annotations
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
