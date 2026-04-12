"""Design Agent — creates cover specs, copy, and renders the HTML landing page."""

from __future__ import annotations
from pathlib import Path
from typing import Any
from jinja2 import Environment, FileSystemLoader

from .base import BaseAgent, _tool_def
from src.models.product import (
    MarketResearch,
    ProductContent,
    DesignAssets,
    CoverDesign,
)
from src import config


SYSTEM = """You are a world-class digital product designer and conversion copywriter.
You craft product experiences that make buyers feel "I need this right now."

Your expertise:
- High-converting landing page copy (headline, sub-headline, bullets, FAQ)
- Visual design direction for digital product covers and mockups
- Colour psychology and font pairing for premium digital products
- Social proof framing and benefit-oriented copywriting
- Mobile-first layout thinking

Rules:
1. Headlines must be specific and outcome-focused — no vague hype.
2. Feature bullets must state the benefit, not just the feature.
3. FAQ must address real objections buyers have ("Is this beginner-friendly?", "What format?", "What if I'm not happy?").
4. Value props must make the product feel like a steal at the listed price.
5. Design direction must be production-ready (specific hex colours, font names, visual concept).
"""


class DesignAgent(BaseAgent):
    SYSTEM = SYSTEM
    MAX_TOKENS = 8192

    def __init__(self, client: Any):
        super().__init__(client, agent_label="design")

    # ── Tools ─────────────────────────────────────────────────────────────────

    @property
    def tools(self) -> list[dict]:
        return [
            _tool_def(
                "save_cover_design",
                "Save the product cover design specification.",
                {
                    "color_scheme": {"type": "string", "description": "2-3 specific hex colours + their roles."},
                    "font_pairing": {"type": "string", "description": "Heading font + body font (e.g. 'Playfair Display + Inter')."},
                    "visual_concept": {"type": "string", "description": "2-3 sentence description of the cover visual concept."},
                    "mockup_description": {
                        "type": "string",
                        "description": "How to present this product as a mockup (device, angle, props, lighting).",
                    },
                },
                ["color_scheme", "font_pairing", "visual_concept", "mockup_description"],
            ),
            _tool_def(
                "save_page_copy",
                "Save all the landing page copy elements.",
                {
                    "hero_headline": {"type": "string", "description": "Main hero headline (<12 words, outcome-focused)."},
                    "hero_subheadline": {"type": "string", "description": "Supporting subheadline (1-2 sentences)."},
                    "value_propositions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-4 top-level value propositions (shown as large feature cards).",
                    },
                    "feature_bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "8-12 benefit-first bullet points for the 'What's Inside' section.",
                    },
                    "social_proof_stats": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-4 social proof stats e.g. '500+ downloads', '4.9/5 stars', '30-day guarantee'.",
                    },
                    "faq": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {"type": "string"},
                                "answer": {"type": "string"},
                            },
                            "required": ["question", "answer"],
                        },
                        "description": "5-7 FAQ entries addressing real buyer objections.",
                    },
                },
                ["hero_headline", "hero_subheadline", "value_propositions", "feature_bullets", "social_proof_stats", "faq"],
            ),
        ]

    def _handle_tool(self, name: str, inputs: dict) -> Any:
        match name:
            case "save_cover_design":
                self._store["cover"] = inputs
            case "save_page_copy":
                self._store["copy"] = inputs
        return {"status": "saved"}

    # ── Public ────────────────────────────────────────────────────────────────

    def run(
        self,
        research: MarketResearch,
        content: ProductContent,
        output_dir: Path,
    ) -> DesignAssets:
        section_titles = [s.title for s in content.sections]
        prompt = (
            f"Design the full product presentation for:\n\n"
            f"PRODUCT: {content.product_name}\n"
            f"SUBTITLE: {content.subtitle}\n"
            f"TAGLINE: {content.tagline}\n"
            f"TYPE: {content.product_type}\n"
            f"PRICE: ${research.recommended_price}\n"
            f"UNIQUE ANGLE: {research.unique_angle}\n\n"
            f"TARGET AUDIENCE:\n"
            f"  {research.target_audience.primary_persona}\n"
            f"  Pain: {', '.join(research.target_audience.pain_points[:3])}\n"
            f"  Desire: {', '.join(research.target_audience.desires[:3])}\n\n"
            f"PRODUCT CONTENTS (sections): {', '.join(section_titles)}\n\n"
            "Use your tools:\n"
            "1. save_cover_design — colours, fonts, visual direction\n"
            "2. save_page_copy — ALL landing page copy\n"
            "3. submit_result — pass a simple confirmation\n\n"
            "Make the landing page copy impossible to ignore."
        )
        super().run(prompt)

        # ── Build models ──────────────────────────────────────────────────────
        cover_raw = self._store.get("cover", {})
        copy_raw = self._store.get("copy", {})

        cover = CoverDesign(
            title=content.product_name,
            subtitle=content.subtitle,
            color_scheme=cover_raw.get("color_scheme", "#6d28d9, #4f46e5, #ffffff"),
            font_pairing=cover_raw.get("font_pairing", "Playfair Display + Inter"),
            visual_concept=cover_raw.get("visual_concept", ""),
            mockup_description=cover_raw.get("mockup_description", ""),
        )

        assets = DesignAssets(
            cover=cover,
            hero_headline=copy_raw.get("hero_headline", content.product_name),
            hero_subheadline=copy_raw.get("hero_subheadline", content.tagline),
            value_propositions=copy_raw.get("value_propositions", []),
            feature_bullets=copy_raw.get("feature_bullets", []),
            social_proof_stats=copy_raw.get("social_proof_stats", []),
            faq=copy_raw.get("faq", []),
        )

        # ── Render HTML page ──────────────────────────────────────────────────
        html_path = self._render_page(assets, research, content, output_dir)
        assets.product_page_path = str(html_path)
        assets.product_page_html = html_path.read_text()

        return assets

    def _render_page(
        self,
        assets: DesignAssets,
        research: MarketResearch,
        content: ProductContent,
        output_dir: Path,
    ) -> Path:
        env = Environment(loader=FileSystemLoader(str(config.TEMPLATES_DIR)), autoescape=True)
        template = env.get_template("product_page.html")

        html = template.render(
            title=content.product_name,
            subtitle=content.subtitle,
            tagline=content.tagline,
            product_type=content.product_type.title(),
            price=research.recommended_price,
            hero_headline=assets.hero_headline,
            hero_subheadline=assets.hero_subheadline,
            value_propositions=assets.value_propositions,
            feature_bullets=assets.feature_bullets,
            social_proof_stats=assets.social_proof_stats,
            faq=assets.faq,
            sections=content.sections,
            cover=assets.cover,
            audience_persona=research.target_audience.primary_persona,
            audience_desires=research.target_audience.desires,
        )

        out = output_dir / "product_page.html"
        out.write_text(html)
        return out
