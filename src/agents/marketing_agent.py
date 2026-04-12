"""Marketing Agent — social posts, email sequences, ad copy, and content calendar."""

from __future__ import annotations
from typing import Any
from .base import BaseAgent, _tool_def
from src.models.product import (
    MarketResearch,
    ProductContent,
    ListingSet,
    MarketingKit,
    SocialPost,
    EmailMessage,
    AdCopy,
)


SYSTEM = """You are a digital product marketing strategist who builds launch campaigns
that generate consistent passive income.

You understand:
- Content marketing that attracts buyers without feeling salesy
- Platform-specific hooks: TikTok/Reels (pattern interrupt), Instagram (aesthetic + value),
  Pinterest (searchable, evergreen), Twitter/X (insight + CTA), Facebook (community-driven)
- Email marketing: welcome sequences, nurture sequences, launch sequences
- Paid ads: Meta (scroll-stopping creative copy), Pinterest (discovery-intent keywords)
- Organic launch strategy: 30-day content calendar

Rules:
1. Every social post must open with a HOOK that stops the scroll.
2. Email subjects must create curiosity or urgency — never boring.
3. Ad copy must state the specific outcome in the first line.
4. The content calendar must mix value content, social proof, and direct offers (80/20 rule).
5. All copy must feel authentic — no "guru speak" or aggressive hype.
6. Pinterest content is evergreen — write it to rank in search.
"""


class MarketingAgent(BaseAgent):
    SYSTEM = SYSTEM
    MAX_TOKENS = 4096
    MAX_ITERATIONS = 35

    def __init__(self, client: Any):
        super().__init__(client, agent_label="marketing")

    # ── Tools ─────────────────────────────────────────────────────────────────

    @property
    def tools(self) -> list[dict]:
        return [
            _tool_def(
                "save_social_post",
                "Save a social media post.",
                {
                    "platform": {
                        "type": "string",
                        "enum": ["instagram", "tiktok", "pinterest", "twitter_x", "facebook"],
                    },
                    "hook": {"type": "string", "description": "Opening line that stops the scroll (<15 words)."},
                    "caption": {"type": "string", "description": "Full post caption."},
                    "hashtags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Relevant hashtags (without #).",
                    },
                    "call_to_action": {"type": "string", "description": "Specific CTA."},
                },
                ["platform", "hook", "caption", "hashtags", "call_to_action"],
            ),
            _tool_def(
                "save_email",
                "Save one email in the sequence.",
                {
                    "send_day": {"type": "integer", "description": "Day in the sequence (0=immediately, 1=day 1, etc.)."},
                    "goal": {"type": "string", "description": "Purpose of this email (e.g. 'welcome', 'value', 'pitch')."},
                    "subject": {"type": "string", "description": "Email subject line."},
                    "preview_text": {"type": "string", "description": "Preview text shown in inbox (<80 chars)."},
                    "body": {"type": "string", "description": "Full email body (conversational, 150-400 words)."},
                },
                ["send_day", "goal", "subject", "preview_text", "body"],
            ),
            _tool_def(
                "save_ad_copy",
                "Save paid ad copy for a specific platform.",
                {
                    "platform": {"type": "string", "enum": ["meta_facebook", "meta_instagram", "pinterest"]},
                    "headline": {"type": "string", "description": "Ad headline (<40 chars for Meta)."},
                    "primary_text": {"type": "string", "description": "Primary ad text / caption."},
                    "description": {"type": "string", "description": "Ad description (shown below headline)."},
                    "call_to_action": {"type": "string", "description": "CTA button text (e.g. 'Shop Now', 'Learn More')."},
                },
                ["platform", "headline", "primary_text", "description", "call_to_action"],
            ),
            _tool_def(
                "save_pinterest_pins",
                "Save Pinterest pin descriptions (evergreen, search-optimised).",
                {
                    "descriptions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "5 pin descriptions, each 150-300 chars, keyword-rich.",
                    }
                },
                ["descriptions"],
            ),
            _tool_def(
                "save_content_calendar",
                "Save 30-day content calendar.",
                {
                    "calendar": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "30 daily content ideas (Day 1: ..., Day 2: ...). Mix value, social proof, offers.",
                    }
                },
                ["calendar"],
            ),
        ]

    def _handle_tool(self, name: str, inputs: dict) -> Any:
        match name:
            case "save_social_post":
                posts: list = self._store.setdefault("social_posts", [])
                posts.append(inputs)
            case "save_email":
                emails: list = self._store.setdefault("emails", [])
                emails.append(inputs)
            case "save_ad_copy":
                ads: list = self._store.setdefault("ads", [])
                ads.append(inputs)
            case "save_pinterest_pins":
                self._store["pinterest_pins"] = inputs.get("descriptions", [])
            case "save_content_calendar":
                self._store["calendar"] = inputs.get("calendar", [])
        return {"status": "saved"}

    # ── Public ────────────────────────────────────────────────────────────────

    def run(
        self,
        research: MarketResearch,
        content: ProductContent,
        listings: ListingSet,
    ) -> MarketingKit:
        buy_link = ""
        if listings.gumroad:
            buy_link = "(link in bio)"

        prompt = (
            f"Create a complete marketing kit for this digital product:\n\n"
            f"PRODUCT: {content.product_name}\n"
            f"TAGLINE: {content.tagline}\n"
            f"PRICE: ${research.recommended_price}\n"
            f"UNIQUE ANGLE: {research.unique_angle}\n"
            f"AUDIENCE: {research.target_audience.primary_persona}\n"
            f"PAIN POINTS: {', '.join(research.target_audience.pain_points[:4])}\n"
            f"DESIRES: {', '.join(research.target_audience.desires[:4])}\n"
            f"WHERE THEY ARE: {', '.join(research.target_audience.where_they_hang_out)}\n\n"
            "Use your tools to build the complete marketing kit:\n"
            "1. save_social_post × 5 (one each: instagram, tiktok, pinterest, twitter_x, facebook)\n"
            "2. save_email × 5 (days 0, 1, 3, 5, 7 — welcome → value → pitch → follow-up → last chance)\n"
            "3. save_ad_copy × 2 (meta_facebook + pinterest)\n"
            "4. save_pinterest_pins (5 evergreen pin descriptions)\n"
            "5. save_content_calendar (30-day plan)\n"
            "6. submit_result\n\n"
            "Make every piece of content feel authentic to each platform's culture."
        )
        super().run(prompt)

        social_posts = [
            SocialPost(
                platform=p["platform"],
                hook=p.get("hook", ""),
                caption=p.get("caption", ""),
                hashtags=p.get("hashtags", []),
                call_to_action=p.get("call_to_action", ""),
            )
            for p in self._store.get("social_posts", [])
        ]

        emails = sorted(self._store.get("emails", []), key=lambda e: e.get("send_day", 0))
        email_messages = [
            EmailMessage(
                send_day=e.get("send_day", 0),
                goal=e.get("goal", ""),
                subject=e.get("subject", ""),
                preview_text=e.get("preview_text", ""),
                body=e.get("body", ""),
            )
            for e in emails
        ]

        ad_copies = [
            AdCopy(
                platform=a["platform"],
                headline=a.get("headline", ""),
                primary_text=a.get("primary_text", ""),
                description=a.get("description", ""),
                call_to_action=a.get("call_to_action", "Shop Now"),
            )
            for a in self._store.get("ads", [])
        ]

        return MarketingKit(
            social_posts=social_posts,
            email_sequence=email_messages,
            ad_copies=ad_copies,
            pinterest_pin_descriptions=self._store.get("pinterest_pins", []),
            content_calendar_30_days=self._store.get("calendar", []),
        )
