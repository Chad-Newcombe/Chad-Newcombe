"""Product Agent — writes the actual digital product content."""

from __future__ import annotations
from typing import Any
from .base import BaseAgent, _tool_def
from src.models.product import MarketResearch, ProductContent, ContentSection


SYSTEM = """You are a master digital product creator — a hybrid of world-class copywriter,
subject-matter expert, and instructional designer.

You create digital products that:
- Deliver genuine, life-changing value (not fluff)
- Are beautifully structured and easy to read
- Contain actionable, step-by-step guidance
- Feel premium and worth more than their price tag
- Are immediately useful the moment someone opens them

Product types you master:
- E-books and ultimate guides (deep, comprehensive)
- Templates and toolkits (plug-and-play)
- Workbooks and action planners (interactive)
- Checklists and cheat sheets (quick-reference)
- Mini-courses and frameworks (systematic)

Rules:
1. NEVER pad content with generic filler — every sentence earns its place.
2. Write like you're talking to a smart, busy person who needs real answers.
3. Each section must have a clear outcome the reader achieves.
4. Include concrete examples, real numbers, specific tools, and tactical advice.
5. Save each section as you write it using the tools.
"""


_CONTENT_PROMPTS = {
    "ebook": "Write a comprehensive e-book with an introduction, 5-8 substantive chapters, and a conclusion.",
    "template": "Create a complete template with instructions, a framework overview, and step-by-step usage guide.",
    "workbook": "Build an actionable workbook with exercises, reflection prompts, and a structured workflow.",
    "checklist": "Produce a meticulous checklist broken into phases/categories with explanatory notes for each item.",
    "guide": "Write an ultimate practical guide with a strong introduction, detailed sections, and clear next steps.",
    "course": "Develop a mini-course with module overviews, lesson content, and action assignments.",
    "planner": "Create a detailed planner with a planning framework, templates, and usage instructions.",
}


class ProductAgent(BaseAgent):
    SYSTEM = SYSTEM
    MAX_TOKENS = 8192
    MAX_ITERATIONS = 40

    def __init__(self, client: Any):
        super().__init__(client, agent_label="product")

    # ── Tools ─────────────────────────────────────────────────────────────────

    @property
    def tools(self) -> list[dict]:
        return [
            _tool_def(
                "save_product_outline",
                "Save the product outline / table of contents before writing content.",
                {
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "key_points": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["title", "key_points"],
                        },
                        "description": "Ordered list of sections/chapters.",
                    }
                },
                ["sections"],
            ),
            _tool_def(
                "save_introduction",
                "Save the product introduction.",
                {
                    "text": {
                        "type": "string",
                        "description": "Full introduction text (200-400 words). Hook the reader, establish credibility, preview what they'll learn.",
                    }
                },
                ["text"],
            ),
            _tool_def(
                "save_section",
                "Save one completed section/chapter.",
                {
                    "title": {"type": "string", "description": "Section title."},
                    "content": {
                        "type": "string",
                        "description": "Full section content (400-800 words). Include examples, tactics, and actionable steps.",
                    },
                },
                ["title", "content"],
            ),
            _tool_def(
                "save_conclusion",
                "Save the product conclusion.",
                {
                    "text": {
                        "type": "string",
                        "description": "Conclusion text (150-300 words). Summarise wins, motivate action, give a clear next step.",
                    }
                },
                ["text"],
            ),
            _tool_def(
                "save_bonus_tips",
                "Save bonus tips or a quick-reference appendix.",
                {
                    "tips": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "5-10 bonus tips, shortcuts, or pro insights.",
                    }
                },
                ["tips"],
            ),
        ]

    def _handle_tool(self, name: str, inputs: dict) -> Any:
        match name:
            case "save_product_outline":
                self._store["outline"] = inputs.get("sections", [])
            case "save_introduction":
                self._store["introduction"] = inputs.get("text", "")
            case "save_section":
                sections: list[dict] = self._store.setdefault("sections", [])
                sections.append(inputs)
            case "save_conclusion":
                self._store["conclusion"] = inputs.get("text", "")
            case "save_bonus_tips":
                self._store["bonus_tips"] = inputs.get("tips", [])
        return {"status": "saved", "sections_so_far": len(self._store.get("sections", []))}

    # ── Public ────────────────────────────────────────────────────────────────

    def run(self, research: MarketResearch) -> ProductContent:
        type_guidance = _CONTENT_PROMPTS.get(
            research.product_type.lower(), _CONTENT_PROMPTS["guide"]
        )
        prompt = (
            f"Create the full digital product based on this market research:\n\n"
            f"PRODUCT NAME: {research.product_name}\n"
            f"SUBTITLE: {research.product_subtitle}\n"
            f"TAGLINE: {research.tagline}\n"
            f"TYPE: {research.product_type}\n"
            f"UNIQUE ANGLE: {research.unique_angle}\n\n"
            f"TARGET AUDIENCE:\n"
            f"  Persona: {research.target_audience.primary_persona}\n"
            f"  Pain points: {', '.join(research.target_audience.pain_points)}\n"
            f"  Desires: {', '.join(research.target_audience.desires)}\n\n"
            f"INSTRUCTION: {type_guidance}\n\n"
            "Use your tools in order:\n"
            "1. save_product_outline — plan all sections first\n"
            "2. save_introduction\n"
            "3. save_section — repeat for each section (be thorough, 400-800 words each)\n"
            "4. save_conclusion\n"
            "5. save_bonus_tips\n"
            "6. submit_result — pass a simple confirmation object\n\n"
            "Write content that earns 5-star reviews."
        )
        super().run(prompt)

        sections = [
            ContentSection(title=s["title"], content=s["content"])
            for s in self._store.get("sections", [])
        ]

        return ProductContent(
            product_name=research.product_name,
            product_type=research.product_type,
            subtitle=research.product_subtitle,
            tagline=research.tagline,
            introduction=self._store.get("introduction", ""),
            sections=sections,
            conclusion=self._store.get("conclusion", ""),
            bonus_tips=self._store.get("bonus_tips", []),
        )
