# Digital Product Agents

A 5-agent AI pipeline that researches, writes, designs, lists, and markets beautiful digital products — fully automated using Claude.

## What It Does

Give it an idea. Get back a complete, ready-to-sell digital product package.

```
outputs/<product-slug>/
├── content.md              ← The full product (ebook, guide, template, etc.)
├── research.json           ← Market research, audience, competitors, pricing
├── product_page.html       ← Beautiful landing page (open in browser)
├── listings/
│   ├── etsy.json           ← Etsy-optimised listing + tags
│   ├── gumroad.json        ← Gumroad story-style listing
│   └── payhip.json         ← Payhip SEO listing
└── marketing/
    ├── social_posts.json   ← Instagram, TikTok, Pinterest, Twitter/X, Facebook
    ├── email_sequence.json ← 5-email welcome → pitch sequence
    ├── ad_copy.json        ← Meta + Pinterest ad copy
    ├── pinterest_pins.json ← 5 evergreen pin descriptions
    └── content_calendar.json ← 30-day content plan
```

## The 5 Agents

| Agent | What It Does |
|-------|-------------|
| **Research** | Market opportunity, target audience, competitors, keywords, pricing |
| **Product** | Writes the full digital product content (sections, intro, conclusion, bonus) |
| **Design** | Creates the HTML landing page + cover design direction |
| **Listing** | Optimises listings for Etsy, Gumroad, and Payhip algorithms |
| **Marketing** | Builds social posts, email sequences, ad copy, and a 30-day calendar |

## Quick Start

### 1. Install dependencies

```bash
pip install -e .
# or
pip install anthropic pydantic rich typer jinja2 python-dotenv
```

### 2. Set your API key

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Create a product

```bash
# E-book
python main.py create "morning routine system for busy entrepreneurs" --type ebook

# Template
python main.py create "Notion CRM for freelancers" --type template

# Workbook
python main.py create "90-day business planning workbook" --type workbook

# Planner
python main.py create "social media content planner for coaches" --type planner
```

### 4. Open your product page

```bash
open outputs/<slug>/product_page.html
```

## Product Types

| Type | Description |
|------|-------------|
| `ebook` | Comprehensive guide (5-8 chapters) |
| `template` | Plug-and-play template with instructions |
| `workbook` | Interactive exercises and prompts |
| `checklist` | Phased checklist with notes |
| `guide` | Practical how-to guide |
| `course` | Mini-course with modules and assignments |
| `planner` | Structured planner with framework |

## Architecture

```
src/
├── orchestrator.py         ← Coordinates all agents
├── agents/
│   ├── base.py             ← Tool-use loop (Anthropic SDK)
│   ├── research_agent.py
│   ├── product_agent.py
│   ├── design_agent.py
│   ├── listing_agent.py
│   └── marketing_agent.py
├── models/product.py       ← Pydantic data models
└── config.py               ← Environment config
templates/
└── product_page.html       ← Tailwind CSS landing page
```

Each agent uses Claude's tool-use API to structure its output step-by-step. Results pass from agent to agent via typed Pydantic models. Prompt caching is applied to system prompts for efficiency.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | required | Your Anthropic API key |
| `CLAUDE_MODEL` | `claude-opus-4-6` | Claude model to use |
| `OUTPUT_DIR` | `./outputs` | Where to save generated products |
