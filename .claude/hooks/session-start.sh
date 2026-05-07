#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Install Python dependencies
pip install -e . --quiet

# Install gstack if not already installed
if [ ! -d "$HOME/.claude/skills/gstack" ]; then
  git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git "$HOME/.claude/skills/gstack"
  cd "$HOME/.claude/skills/gstack" && ./setup --team
fi
