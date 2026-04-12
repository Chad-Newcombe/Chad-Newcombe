"""Orchestrator — coordinates all agents and saves outputs."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box

from src import config
from src.agents.research_agent import ResearchAgent
from src.agents.product_agent import ProductAgent
from src.agents.design_agent import DesignAgent
from src.agents.listing_agent import ListingAgent
from src.agents.marketing_agent import MarketingAgent
from src.models.product import DigitalProduct

console = Console()

STEPS = [
    ("Research", "Analysing market, audience, and competition"),
    ("Product", "Writing product content"),
    ("Design", "Designing landing page and visual assets"),
    ("Listings", "Creating marketplace listings"),
    ("Marketing", "Building marketing kit"),
]


class Orchestrator:
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key or config.ANTHROPIC_API_KEY)
        self.research_agent = ResearchAgent(self.client)
        self.product_agent = ProductAgent(self.client)
        self.design_agent = DesignAgent(self.client)
        self.listing_agent = ListingAgent(self.client)
        self.marketing_agent = MarketingAgent(self.client)

    # ── Public API ────────────────────────────────────────────────────────────

    def create_product(self, idea: str, product_type: str = "ebook") -> DigitalProduct:
        """Run the full pipeline and return a completed DigitalProduct."""
        console.print(
            Panel.fit(
                f"[bold cyan]Digital Product Agents[/bold cyan]\n"
                f"[dim]Idea:[/dim] [white]{idea}[/white]\n"
                f"[dim]Type:[/dim] [white]{product_type}[/white]",
                border_style="cyan",
                padding=(1, 4),
            )
        )

        # ── Step 1: Research ──────────────────────────────────────────────────
        console.print("\n[bold yellow]Step 1/5 — Market Research[/bold yellow]")
        with _spinner("Researching market opportunities…"):
            research = self.research_agent.run(idea, product_type)
        _step_done(f"{research.product_name} | ${research.recommended_price}")

        # ── Step 2: Product ───────────────────────────────────────────────────
        console.print("\n[bold yellow]Step 2/5 — Creating Product[/bold yellow]")
        with _spinner("Writing product content…"):
            content = self.product_agent.run(research)
        _step_done(f"{len(content.sections)} sections | {content.total_word_count:,} words")

        # ── Step 3: Design ────────────────────────────────────────────────────
        console.print("\n[bold yellow]Step 3/5 — Designing Assets[/bold yellow]")
        output_dir = _make_output_dir(research.product_name)
        with _spinner("Designing landing page…"):
            design = self.design_agent.run(research, content, output_dir)
        _step_done("product_page.html rendered")

        # ── Step 4: Listings ──────────────────────────────────────────────────
        console.print("\n[bold yellow]Step 4/5 — Creating Listings[/bold yellow]")
        with _spinner("Writing marketplace listings…"):
            listings = self.listing_agent.run(research, content)
        platforms = [p for p, v in listings.model_dump().items() if v is not None]
        _step_done(f"{len(platforms)} listings: {', '.join(platforms)}")

        # ── Step 5: Marketing ─────────────────────────────────────────────────
        console.print("\n[bold yellow]Step 5/5 — Building Marketing Kit[/bold yellow]")
        with _spinner("Crafting marketing materials…"):
            marketing = self.marketing_agent.run(research, content, listings)
        _step_done(
            f"{len(marketing.social_posts)} social posts | "
            f"{len(marketing.email_sequence)} emails | "
            f"{len(marketing.ad_copies)} ads"
        )

        product = DigitalProduct(
            research=research,
            content=content,
            design=design,
            listings=listings,
            marketing=marketing,
            output_dir=str(output_dir),
        )

        # ── Save all outputs ──────────────────────────────────────────────────
        self._save_outputs(product, output_dir)
        self._print_summary(product, output_dir)

        return product

    # ── Private ───────────────────────────────────────────────────────────────

    def _save_outputs(self, product: DigitalProduct, output_dir: Path) -> None:
        # Markdown content
        (output_dir / "content.md").write_text(product.content.to_markdown())

        # Research JSON
        (output_dir / "research.json").write_text(
            product.research.model_dump_json(indent=2)
        )

        # Listings
        listings_dir = output_dir / "listings"
        listings_dir.mkdir(exist_ok=True)
        for platform, listing in product.listings.model_dump().items():
            if listing:
                (listings_dir / f"{platform}.json").write_text(
                    json.dumps(listing, indent=2)
                )

        # Marketing
        marketing_dir = output_dir / "marketing"
        marketing_dir.mkdir(exist_ok=True)
        (marketing_dir / "social_posts.json").write_text(
            json.dumps(
                [p.model_dump() for p in product.marketing.social_posts], indent=2
            )
        )
        (marketing_dir / "email_sequence.json").write_text(
            json.dumps(
                [e.model_dump() for e in product.marketing.email_sequence], indent=2
            )
        )
        (marketing_dir / "ad_copy.json").write_text(
            json.dumps(
                [a.model_dump() for a in product.marketing.ad_copies], indent=2
            )
        )
        (marketing_dir / "pinterest_pins.json").write_text(
            json.dumps(product.marketing.pinterest_pin_descriptions, indent=2)
        )
        (marketing_dir / "content_calendar.json").write_text(
            json.dumps(product.marketing.content_calendar_30_days, indent=2)
        )

    def _print_summary(self, product: DigitalProduct, output_dir: Path) -> None:
        console.print()
        table = Table(
            title="[bold green]Product Package Complete[/bold green]",
            box=box.ROUNDED,
            border_style="green",
            show_header=True,
            header_style="bold white",
        )
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")

        table.add_row("content.md", f"{product.content.total_word_count:,} words")
        table.add_row("research.json", f"Market research + {len(product.research.competitors)} competitors")
        table.add_row("product_page.html", "Ready-to-publish landing page")

        for platform, data in product.listings.model_dump().items():
            if data:
                table.add_row(f"listings/{platform}.json", f"${data['price']} — {len(data['tags'])} tags")

        table.add_row("marketing/social_posts.json", f"{len(product.marketing.social_posts)} platform posts")
        table.add_row("marketing/email_sequence.json", f"{len(product.marketing.email_sequence)}-email sequence")
        table.add_row("marketing/ad_copy.json", f"{len(product.marketing.ad_copies)} ad creatives")
        table.add_row("marketing/pinterest_pins.json", f"{len(product.marketing.pinterest_pin_descriptions)} pin descriptions")
        table.add_row("marketing/content_calendar.json", "30-day content plan")

        console.print(table)
        console.print(f"\n[dim]Output directory:[/dim] [bold]{output_dir}[/bold]")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_output_dir(product_name: str) -> Path:
    slug = product_name.lower().replace(" ", "-").replace("'", "").replace(":", "")[:50]
    output_dir = config.OUTPUT_DIR / slug
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _spinner(message: str):
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[dim]{message}[/dim]"),
        transient=True,
        console=console,
    )


def _step_done(detail: str) -> None:
    console.print(f"  [bold green]✓[/bold green] [dim]{detail}[/dim]")
