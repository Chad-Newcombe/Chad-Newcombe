"""Listing Agent — creates optimised marketplace listings."""

from __future__ import annotations
from typing import Any
from .base import BaseAgent, _tool_def
from src.models.product import (
    MarketResearch,
    ProductContent,
    Listing,
    ListingSet,
)


SYSTEM = """You are a marketplace listing specialist who has generated millions of dollars
in digital product sales on Etsy, Gumroad, Payhip, and Creative Market.

You know the exact patterns that get listings to rank and convert:
- Etsy: 140-char title packed with keywords, keyword-rich description with line breaks,
  13 highly relevant tags (max 20 chars each), correct category paths
- Gumroad: compelling story-driven description, clear "what you get", pricing psychology
- Payhip: SEO meta description, benefit-led copy, clear file format info
- Creative Market: professional tone, target audience callout, license clarity

Rules:
1. Titles must lead with the highest-volume keyword, not the product name.
2. Descriptions open with the buyer's pain, not product features.
3. Tags must be what buyers TYPE, not what sellers think sounds good.
4. Always mention: file format, page count or template count, instant download.
5. Optimise for the specific platform's search algorithm.
"""


_PLATFORM_GUIDANCE = {
    "etsy": {
        "title_limit": 140,
        "description_note": "Use short paragraphs. Include keywords naturally. Mention 'instant digital download'.",
        "tag_limit": 13,
        "tag_char_limit": 20,
        "category": "Digital Downloads > E-books & Guides",
    },
    "gumroad": {
        "title_limit": 200,
        "description_note": "Tell a story. Use markdown. Open with the problem, reveal the solution, list what's included.",
        "tag_limit": 10,
        "tag_char_limit": 50,
        "category": "Education",
    },
    "payhip": {
        "title_limit": 200,
        "description_note": "SEO-friendly. Include meta description. Professional tone.",
        "tag_limit": 10,
        "tag_char_limit": 30,
        "category": "Digital Download",
    },
}


class ListingAgent(BaseAgent):
    SYSTEM = SYSTEM
    MAX_TOKENS = 4096

    def __init__(self, client: Any):
        super().__init__(client, agent_label="listing")

    # ── Tools ─────────────────────────────────────────────────────────────────

    @property
    def tools(self) -> list[dict]:
        return [
            _tool_def(
                "save_listing",
                "Save a completed marketplace listing.",
                {
                    "platform": {
                        "type": "string",
                        "enum": ["etsy", "gumroad", "payhip", "creative_market"],
                        "description": "Target platform.",
                    },
                    "title": {"type": "string", "description": "Listing title (keyword-optimised for that platform)."},
                    "description": {
                        "type": "string",
                        "description": "Full listing description (platform-appropriate formatting).",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Search tags/keywords for the platform.",
                    },
                    "price": {"type": "number", "description": "Listing price in USD."},
                    "category": {"type": "string", "description": "Platform-specific category path."},
                    "file_formats": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File formats included (e.g. PDF, EPUB, Notion link).",
                    },
                },
                ["platform", "title", "description", "tags", "price", "category", "file_formats"],
            )
        ]

    def _handle_tool(self, name: str, inputs: dict) -> Any:
        if name == "save_listing":
            platform = inputs.get("platform", "")
            self._store[platform] = inputs
        return {"status": "saved", "platform": inputs.get("platform")}

    # ── Public ────────────────────────────────────────────────────────────────

    def run(self, research: MarketResearch, content: ProductContent) -> ListingSet:
        section_titles = [s.title for s in content.sections]
        keywords_str = ", ".join(research.top_keywords[:10])

        prompt = (
            f"Create marketplace listings for this digital product:\n\n"
            f"PRODUCT NAME: {content.product_name}\n"
            f"TYPE: {content.product_type}\n"
            f"PRICE: ${research.recommended_price}\n"
            f"TAGLINE: {content.tagline}\n"
            f"UNIQUE ANGLE: {research.unique_angle}\n"
            f"AUDIENCE: {research.target_audience.primary_persona}\n"
            f"TOP KEYWORDS: {keywords_str}\n"
            f"SECTIONS/CHAPTERS: {', '.join(section_titles)}\n\n"
            "Create listings for ALL THREE platforms: etsy, gumroad, payhip.\n"
            "Use save_listing for each platform, then submit_result.\n\n"
            "Platform guidance:\n"
            "- Etsy: 140-char title starting with the top keyword. 13 tags ≤20 chars each.\n"
            "- Gumroad: Story-driven, markdown description. Lead with buyer's pain point.\n"
            "- Payhip: Professional, SEO-focused. Include clear file format details.\n\n"
            "Each listing must feel native to its platform."
        )
        super().run(prompt)

        def _build(platform: str) -> Listing | None:
            data = self._store.get(platform)
            if not data:
                return None
            return Listing(
                platform=platform,
                title=data.get("title", content.product_name),
                description=data.get("description", ""),
                tags=data.get("tags", []),
                price=float(data.get("price", research.recommended_price)),
                category=data.get("category", "Digital Downloads"),
                file_formats=data.get("file_formats", ["PDF"]),
            )

        return ListingSet(
            etsy=_build("etsy"),
            gumroad=_build("gumroad"),
            payhip=_build("payhip"),
        )
