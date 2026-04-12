"""Research Agent — analyses markets, audiences, competitors, and pricing."""

from __future__ import annotations
from typing import Any
from .base import BaseAgent, _tool_def
from src.models.product import (
    MarketResearch,
    CompetitorProduct,
    TargetAudience,
)


SYSTEM = """You are a world-class digital product market researcher with deep expertise in:
- Digital product marketplaces (Etsy, Gumroad, Payhip, Creative Market, Teachable)
- Niche identification and validation for info-products, templates, and e-books
- Consumer psychology and buyer behaviour for impulse & considered digital purchases
- SEO keyword research for marketplace search algorithms
- Competitive analysis and differentiation strategy
- Pricing strategy for digital downloads ($7–$197 range)

Your job: given an idea + product type, produce a thorough market brief that the product-creation agent will use to build something that actually sells.

Rules:
1. Be specific and opinionated. Generic advice is useless.
2. Provide real keyword phrases people type into Etsy/Google.
3. Name a concrete, differentiated angle that will cut through existing products.
4. Recommend a confident price point with reasoning.
5. Use your tools to save each piece of research before submitting the final result.
"""


class ResearchAgent(BaseAgent):
    SYSTEM = SYSTEM
    MAX_TOKENS = 4096

    def __init__(self, client: Any):
        super().__init__(client, agent_label="research")
        self._audience: dict = {}
        self._competitors: list[dict] = []
        self._keywords: list[str] = []
        self._pricing: dict = {}
        self._opportunity: str = ""

    # ── Tools ─────────────────────────────────────────────────────────────────

    @property
    def tools(self) -> list[dict]:
        return [
            _tool_def(
                "save_opportunity_analysis",
                "Save the market opportunity analysis text.",
                {
                    "summary": {"type": "string", "description": "Opportunity summary (2-4 paragraphs)."},
                    "unique_angle": {"type": "string", "description": "The specific differentiated angle for this product."},
                    "product_name": {"type": "string", "description": "Proposed product name."},
                    "product_subtitle": {"type": "string", "description": "Proposed subtitle (one line)."},
                    "tagline": {"type": "string", "description": "Short punchy tagline (<10 words)."},
                },
                ["summary", "unique_angle", "product_name", "product_subtitle", "tagline"],
            ),
            _tool_def(
                "save_target_audience",
                "Save the target audience profile.",
                {
                    "primary_persona": {"type": "string", "description": "One-sentence persona description."},
                    "pain_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "4-6 specific pain points.",
                    },
                    "desires": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "4-6 specific desires/outcomes they want.",
                    },
                    "demographics": {"type": "string", "description": "Age range, occupation, income, lifestyle."},
                    "where_they_hang_out": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Platforms and communities they use (Pinterest, Reddit subs, Instagram etc.).",
                    },
                },
                ["primary_persona", "pain_points", "desires", "demographics", "where_they_hang_out"],
            ),
            _tool_def(
                "save_competitor_products",
                "Save a list of real competitor products.",
                {
                    "competitors": {
                        "type": "array",
                        "description": "3-5 competitor products.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "platform": {"type": "string"},
                                "price": {"type": "number"},
                                "strengths": {"type": "array", "items": {"type": "string"}},
                                "weaknesses": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["name", "platform", "price", "strengths", "weaknesses"],
                        },
                    }
                },
                ["competitors"],
            ),
            _tool_def(
                "save_keyword_research",
                "Save keyword research — phrases buyers actually search.",
                {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "10-15 keyword phrases sorted by relevance.",
                    }
                },
                ["keywords"],
            ),
            _tool_def(
                "save_pricing_strategy",
                "Save recommended pricing with rationale.",
                {
                    "recommended_price": {"type": "number", "description": "Recommended price in USD."},
                    "rationale": {"type": "string", "description": "Why this price? Reference competitor pricing."},
                },
                ["recommended_price", "rationale"],
            ),
        ]

    def _handle_tool(self, name: str, inputs: dict) -> Any:
        match name:
            case "save_opportunity_analysis":
                self._store["opportunity"] = inputs
            case "save_target_audience":
                self._store["audience"] = inputs
            case "save_competitor_products":
                self._store["competitors"] = inputs.get("competitors", [])
            case "save_keyword_research":
                self._store["keywords"] = inputs.get("keywords", [])
            case "save_pricing_strategy":
                self._store["pricing"] = inputs
        return {"status": "saved"}

    # ── Public ────────────────────────────────────────────────────────────────

    def run(self, idea: str, product_type: str) -> MarketResearch:
        prompt = (
            f"Research the digital product market for this idea:\n\n"
            f"IDEA: {idea}\n"
            f"PRODUCT TYPE: {product_type}\n\n"
            "Use your tools systematically:\n"
            "1. save_opportunity_analysis — market opportunity, unique angle, product name\n"
            "2. save_target_audience — detailed buyer persona\n"
            "3. save_competitor_products — 3-5 real competitors\n"
            "4. save_keyword_research — 10-15 search phrases\n"
            "5. save_pricing_strategy — recommended price\n"
            "6. submit_result — the complete MarketResearch object\n\n"
            "The submit_result must contain ALL fields needed by the pipeline."
        )
        raw = super().run(prompt)

        # Build from stored data + raw result
        opp = self._store.get("opportunity", {})
        aud = self._store.get("audience", {})
        competitors_raw = self._store.get("competitors", [])
        pricing = self._store.get("pricing", {})

        competitors = [
            CompetitorProduct(**c)
            for c in competitors_raw
            if all(k in c for k in ["name", "platform", "price", "strengths", "weaknesses"])
        ]

        target_audience = TargetAudience(
            primary_persona=aud.get("primary_persona", raw.get("primary_persona", "")),
            pain_points=aud.get("pain_points", raw.get("pain_points", [])),
            desires=aud.get("desires", raw.get("desires", [])),
            demographics=aud.get("demographics", raw.get("demographics", "")),
            where_they_hang_out=aud.get("where_they_hang_out", raw.get("where_they_hang_out", [])),
        )

        return MarketResearch(
            niche=idea,
            product_type=product_type,
            opportunity_summary=opp.get("summary", raw.get("opportunity_summary", "")),
            target_audience=target_audience,
            competitors=competitors,
            recommended_price=float(pricing.get("recommended_price", raw.get("recommended_price", 27))),
            price_rationale=pricing.get("rationale", raw.get("price_rationale", "")),
            top_keywords=self._store.get("keywords", raw.get("top_keywords", [])),
            unique_angle=opp.get("unique_angle", raw.get("unique_angle", "")),
            product_name=opp.get("product_name", raw.get("product_name", idea)),
            product_subtitle=opp.get("product_subtitle", raw.get("product_subtitle", "")),
            tagline=opp.get("tagline", raw.get("tagline", "")),
        )
