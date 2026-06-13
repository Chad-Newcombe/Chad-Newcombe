# Personal Finance Analyzer + Digital Product Agents

Two AI toolkits in one repo, both powered by Claude:

1. **💰 Personal Finance Analyzer** — upload your bank & credit card statements and get categorized spending, debt payoff plans, a budget, and a month-by-month action plan. CLI **and** web dashboard.
2. **📦 Digital Product Agents** — a 5-agent pipeline that researches, writes, designs, lists, and markets a complete digital product from a single idea.

---

# 💰 Personal Finance Analyzer

Point it at your CSV statements. Claude categorizes every transaction, then the tool
computes debt payoff strategies, a 50/30/20 budget, and a personalized plan for the
months ahead.

## What You Get

```
outputs/finance-YYYY-MM-DD/
├── finance_report.md      ← human-readable summary (start here)
├── report.json            ← complete structured data
├── transactions.json      ← every transaction, categorized
├── debt_payoff.json       ← avalanche + snowball schedules
└── budget.json            ← 50/30/20 budget plan
```

- **Categorized spending** — Claude reads merchant names and sorts transactions into 13 categories (groceries, dining, utilities, transport, debt payments, income, …).
- **Debt payoff plans** — both **avalanche** (highest APR first, minimizes interest) and **snowball** (smallest balance first, fastest wins), with month-by-month schedules.
- **50/30/20 budget** — your actual spending mapped to needs / wants / savings-debt, vs. targets.
- **Projected income** — use your real expected take-home pay instead of a noisy statement average.
- **Monthly action plans** — concrete steps, payment targets, and milestones for the next 3–6 months, written by Claude.

## Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Set your API key

```bash
cp .env.example .env   # then add your ANTHROPIC_API_KEY
```

### 3a. Run on the command line

```bash
python main.py analyze sample_data/checking.csv sample_data/visa.csv \
    --cc "Visa:21.99:25" \
    --income 3500 \
    --budget 600
```

### 3b. …or use the web dashboard

```bash
python main.py serve
# open http://127.0.0.1:5000
```

Upload your CSVs, enter each card's APR / minimum payment, and view an interactive
dashboard with charts, the avalanche-vs-snowball comparison, a searchable transaction
table, and your monthly action plans.

## CLI Reference

```bash
python main.py analyze <statements...> [options]
```

| Option | Description |
|--------|-------------|
| `statements` | One or more CSV files (bank + credit cards) |
| `--cc`, `-c` | Credit card config: `"name:APR:min_payment"` (repeatable). Optional 4th/5th fields: `:balance:limit` |
| `--income`, `-i` | Projected monthly take-home income (else historical average is used) |
| `--budget`, `-b` | Total monthly dollars for debt repayment (else auto-calculated) |
| `--api-key`, `-k` | Anthropic API key (or set `ANTHROPIC_API_KEY`) |

**Credit card config** pairs to a statement by name match. For a card with a balance
of $2,400 and a $5,000 limit at 21.99% APR with a $25 minimum:

```bash
--cc "Visa:21.99:25:2400:5000"
```

If `--budget` is omitted it defaults to the sum of minimum payments plus 30% of your
net monthly cash flow.

## CSV Format

The parser auto-detects common column names — no reformatting needed:

| Field | Recognized headers |
|-------|-------------------|
| Date | `Date`, `Transaction Date`, `Posted Date` |
| Description | `Description`, `Merchant`, `Payee`, `Details`, `Memo` |
| Amount | `Amount`, or separate `Debit` / `Credit` columns |
| Balance | `Balance`, `Running Balance` |

Sign convention: negative = money out, positive = money in. Credit card exports that
list charges as positive numbers are auto-normalized when the file is paired with `--cc`.

See `sample_data/` for example files and a sample generated report.

## How It Works

```
CSV files → parser → CategorizationAgent (AI) → analyzer → PlanningAgent (AI) → report
            (pure)    (Claude tool-use)          (pure)      (Claude tool-use)
```

- **Parsing, debt math, and budget framework are pure Python** — deterministic and unit-tested.
- **Categorization and the narrative plan use Claude** via the same tool-use `BaseAgent` loop as the product pipeline.

The debt simulation accrues monthly interest, pays minimums on every card, then cascades
any surplus to the priority card (avalanche or snowball). It guarantees the accounting
identity *total interest paid = total payments − original principal*.

## Tests

The pure-Python logic (parser, snapshot, debt payoff, budget) is fully unit-tested and
needs no API key:

```bash
pytest tests/
```

---

# 📦 Digital Product Agents

A 5-agent AI pipeline that turns one idea into a complete, ready-to-sell digital product package.

```bash
python main.py create "morning routine system for busy entrepreneurs" --type ebook
```

Produces:

```
outputs/<product-slug>/
├── content.md              ← The full product
├── research.json           ← Market research, audience, competitors, pricing
├── product_page.html       ← Landing page (open in browser)
├── listings/               ← Etsy, Gumroad, Payhip listings
└── marketing/              ← Social posts, emails, ad copy, 30-day calendar
```

| Agent | What It Does |
|-------|-------------|
| **Research** | Market opportunity, audience, competitors, keywords, pricing |
| **Product** | Writes the full product content |
| **Design** | HTML landing page + cover direction |
| **Listing** | Optimized listings for Etsy, Gumroad, Payhip |
| **Marketing** | Social posts, email sequence, ad copy, 30-day calendar |

**Product types:** `ebook`, `template`, `workbook`, `checklist`, `guide`, `course`, `planner`
(run `python main.py types` for descriptions).

---

## Architecture

```
main.py                       ← Typer CLI: analyze, serve, create, types
src/
├── config.py                 ← Environment config
├── agents/
│   ├── base.py               ← Claude tool-use loop (shared by all agents)
│   ├── categorization_agent.py   ← Finance: categorize transactions
│   ├── planning_agent.py         ← Finance: narrative + monthly plans
│   └── research/product/design/listing/marketing_agent.py   ← Product pipeline
├── finance/
│   ├── parser.py             ← CSV parsing (auto-detect columns)
│   ├── analyzer.py           ← Debt payoff, snapshot, budget framework
│   └── report_writer.py      ← Markdown report
├── finance_orchestrator.py   ← Finance pipeline coordinator
├── orchestrator.py           ← Product pipeline coordinator
└── models/
    ├── finance.py            ← Finance Pydantic models
    └── product.py            ← Product Pydantic models
web/                          ← Flask dashboard (upload, dashboard, transactions)
tests/                        ← Pure-Python unit tests
sample_data/                  ← Example CSVs + sample report
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | required | Your Anthropic API key |
| `CLAUDE_MODEL` | `claude-opus-4-6` | Claude model to use |
| `OUTPUT_DIR` | `./outputs` | Where to save results |
