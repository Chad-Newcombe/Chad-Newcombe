"""Configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "./outputs"))
TEMPLATES_DIR: Path = Path(__file__).parent.parent / "templates"

# Token limits per agent
RESEARCH_MAX_TOKENS = 4096
PRODUCT_MAX_TOKENS = 8192
DESIGN_MAX_TOKENS = 8192
LISTING_MAX_TOKENS = 4096
MARKETING_MAX_TOKENS = 4096
