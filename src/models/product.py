"""Pydantic models for the digital product pipeline."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


# ── Research ──────────────────────────────────────────────────────────────────

class CompetitorProduct(BaseModel):
    name: str
    platform: str
    price: float
    strengths: list[str]
    weaknesses: list[str]


class TargetAudience(BaseModel):
    primary_persona: str
    pain_points: list[str]
    desires: list[str]
    demographics: str
    where_they_hang_out: list[str]


class MarketResearch(BaseModel):
    niche: str
    product_type: str
    opportunity_summary: str
    target_audience: TargetAudience
    competitors: list[CompetitorProduct]
    recommended_price: float
    price_rationale: str
    top_keywords: list[str]
    unique_angle: str
    product_name: str
    product_subtitle: str
    tagline: str


# ── Product Content ───────────────────────────────────────────────────────────

class ContentSection(BaseModel):
    title: str
    content: str
    word_count: int = 0

    def model_post_init(self, __context: object) -> None:
        if not self.word_count:
            self.word_count = len(self.content.split())


class ProductContent(BaseModel):
    product_name: str
    product_type: str
    subtitle: str
    tagline: str
    introduction: str
    sections: list[ContentSection]
    conclusion: str
    bonus_tips: list[str] = Field(default_factory=list)

    @property
    def total_word_count(self) -> int:
        total = len(self.introduction.split()) + len(self.conclusion.split())
        return total + sum(s.word_count for s in self.sections)

    def to_markdown(self) -> str:
        lines: list[str] = [
            f"# {self.product_name}",
            f"### {self.subtitle}",
            f"> {self.tagline}",
            "",
            "---",
            "",
            "## Introduction",
            "",
            self.introduction,
            "",
        ]
        for i, section in enumerate(self.sections, 1):
            lines += [f"## {i}. {section.title}", "", section.content, ""]

        lines += [
            "## Conclusion",
            "",
            self.conclusion,
            "",
        ]

        if self.bonus_tips:
            lines += ["## Bonus Tips", ""]
            for tip in self.bonus_tips:
                lines.append(f"- {tip}")

        return "\n".join(lines)


# ── Design ────────────────────────────────────────────────────────────────────

class CoverDesign(BaseModel):
    title: str
    subtitle: str
    color_scheme: str
    font_pairing: str
    visual_concept: str
    mockup_description: str


class DesignAssets(BaseModel):
    cover: CoverDesign
    hero_headline: str
    hero_subheadline: str
    value_propositions: list[str]
    feature_bullets: list[str]
    social_proof_stats: list[str]
    faq: list[dict[str, str]]
    product_page_html: str = ""
    product_page_path: str = ""


# ── Listings ──────────────────────────────────────────────────────────────────

class Listing(BaseModel):
    platform: str
    title: str
    description: str
    tags: list[str]
    price: float
    category: str
    file_formats: list[str]
    instant_download: bool = True


class ListingSet(BaseModel):
    etsy: Optional[Listing] = None
    gumroad: Optional[Listing] = None
    payhip: Optional[Listing] = None
    creative_market: Optional[Listing] = None


# ── Marketing ─────────────────────────────────────────────────────────────────

class SocialPost(BaseModel):
    platform: str
    caption: str
    hashtags: list[str]
    hook: str
    call_to_action: str


class EmailMessage(BaseModel):
    subject: str
    preview_text: str
    body: str
    send_day: int
    goal: str


class AdCopy(BaseModel):
    platform: str
    headline: str
    primary_text: str
    description: str
    call_to_action: str


class MarketingKit(BaseModel):
    social_posts: list[SocialPost]
    email_sequence: list[EmailMessage]
    ad_copies: list[AdCopy]
    pinterest_pin_descriptions: list[str]
    content_calendar_30_days: list[str]


# ── Complete Product ───────────────────────────────────────────────────────────

class DigitalProduct(BaseModel):
    research: MarketResearch
    content: ProductContent
    design: DesignAssets
    listings: ListingSet
    marketing: MarketingKit
    output_dir: str = ""
