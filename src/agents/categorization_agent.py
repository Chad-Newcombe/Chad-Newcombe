"""AI agent that categorizes bank/credit card transactions in batches."""

from __future__ import annotations
import json
from typing import Any

from src.agents.base import BaseAgent, _tool_def
from src.models.finance import Transaction, TransactionCategory

_BATCH_SIZE = 60

_VALID_CATEGORIES = [c.value for c in TransactionCategory]

SAVE_TOOL = _tool_def(
    name="save_categorized_transactions",
    description=(
        "Save the category assignments for a batch of transactions. "
        "Call this once you have categorized all transactions in the current batch."
    ),
    properties={
        "categorizations": {
            "type": "array",
            "description": "List of category assignments.",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "The transaction index from the batch."},
                    "category": {
                        "type": "string",
                        "enum": _VALID_CATEGORIES,
                        "description": "The assigned category.",
                    },
                    "is_transfer": {
                        "type": "boolean",
                        "description": "True if this is an internal transfer (e.g. credit card payment from checking).",
                    },
                },
                "required": ["id", "category", "is_transfer"],
            },
        }
    },
    required=["categorizations"],
)


class CategorizationAgent(BaseAgent):
    SYSTEM = (
        "You are an expert at reading bank and credit card statement descriptions and "
        "assigning them to the correct spending category. You understand common merchant "
        "names, abbreviations, and bank transaction codes.\n\n"
        "Categories available:\n"
        "- income: paychecks, direct deposits, interest earned, refunds\n"
        "- housing: rent, mortgage, HOA, home insurance, property tax\n"
        "- groceries: supermarkets, grocery stores, warehouse clubs (Costco, Sam's Club)\n"
        "- dining: restaurants, fast food, cafes, food delivery (DoorDash, Uber Eats)\n"
        "- utilities: electricity, gas, water, internet, phone, trash\n"
        "- transport: gas stations, parking, tolls, rideshare, car payment, auto insurance, public transit\n"
        "- entertainment: movies, concerts, streaming (Netflix, Spotify), games, hobbies\n"
        "- healthcare: pharmacy, doctor, dentist, hospital, health insurance\n"
        "- clothing: apparel stores, shoes, online clothing retailers\n"
        "- debt_payment: credit card payments, loan payments, student loans (when it's a debt payoff, not a purchase)\n"
        "- savings: transfers to savings account, investments, 401k, brokerage\n"
        "- subscriptions: software, apps, memberships not covered by other categories\n"
        "- other: anything that doesn't fit above\n\n"
        "Mark is_transfer=true for transactions that move money between the user's own accounts "
        "(e.g., 'PAYMENT THANK YOU', 'ONLINE PAYMENT', 'TRANSFER TO CHECKING')."
    )
    MAX_TOKENS = 8192
    MAX_ITERATIONS = 20

    @property
    def tools(self) -> list[dict]:
        return [SAVE_TOOL]

    def _handle_tool(self, name: str, inputs: dict) -> Any:
        if name == "save_categorized_transactions":
            self._store.setdefault("categorizations", []).extend(inputs["categorizations"])
            return {"status": "saved", "count": len(inputs["categorizations"])}
        raise NotImplementedError(f"Unhandled tool: {name}")

    def run_categorization(self, transactions: list[Transaction]) -> list[Transaction]:
        """Categorize all transactions in batches; return updated list."""
        result = list(transactions)

        for batch_start in range(0, len(transactions), _BATCH_SIZE):
            batch = transactions[batch_start: batch_start + _BATCH_SIZE]
            self._store["categorizations"] = []

            batch_json = json.dumps(
                [
                    {"id": i, "date": t.date, "description": t.description, "amount": t.amount}
                    for i, t in enumerate(batch)
                ],
                indent=2,
            )
            prompt = (
                f"Please categorize these {len(batch)} transactions. "
                "Call save_categorized_transactions once with ALL categorizations.\n\n"
                f"```json\n{batch_json}\n```"
            )
            super().run(prompt)

            for entry in self._store.get("categorizations", []):
                idx = batch_start + entry["id"]
                if 0 <= idx < len(result):
                    try:
                        result[idx] = result[idx].model_copy(update={
                            "category": TransactionCategory(entry["category"]),
                            "is_transfer": bool(entry.get("is_transfer", False)),
                        })
                    except (ValueError, KeyError):
                        pass

        return result
