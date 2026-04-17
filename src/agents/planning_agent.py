"""AI agent that generates financial narrative, recommendations, and monthly action plans."""

from __future__ import annotations
import json
from typing import Any

from src.agents.base import BaseAgent, _tool_def
from src.models.finance import (
    BudgetPlan,
    DebtPayoffPlan,
    FinancialSnapshot,
    MonthlyActionPlan,
)

SUMMARY_TOOL = _tool_def(
    name="save_executive_summary",
    description="Save the executive summary — a 2-3 paragraph narrative overview of the user's financial health.",
    properties={
        "summary": {"type": "string", "description": "The executive summary text."}
    },
    required=["summary"],
)

RECOMMENDATIONS_TOOL = _tool_def(
    name="save_recommendations",
    description="Save the top 5-8 prioritized action recommendations.",
    properties={
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of concrete, actionable recommendations.",
        }
    },
    required=["recommendations"],
)

MONTHLY_PLAN_TOOL = _tool_def(
    name="save_monthly_plan",
    description=(
        "Save the action plan for a single upcoming month. "
        "Call this once per month you want to plan (e.g., 3-6 times total)."
    ),
    properties={
        "month": {"type": "string", "description": 'Month label, e.g. "May 2026".'},
        "priority_actions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3-5 specific actions to take this month.",
        },
        "debt_payments": {
            "type": "object",
            "description": "Map of account name to recommended payment amount.",
            "additionalProperties": {"type": "number"},
        },
        "savings_target": {"type": "number", "description": "Dollar amount to save this month."},
        "budget_targets": {
            "type": "object",
            "description": "Map of spending category to recommended monthly budget.",
            "additionalProperties": {"type": "number"},
        },
        "key_milestones": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Milestones or goals to hit this month.",
        },
    },
    required=["month", "priority_actions", "debt_payments", "savings_target", "budget_targets", "key_milestones"],
)


class PlanningAgent(BaseAgent):
    SYSTEM = (
        "You are a Certified Financial Planner (CFP) helping a client build a realistic, "
        "actionable personal finance plan. You specialize in debt payoff strategies, "
        "budgeting, and cash flow optimization.\n\n"
        "Your tone is warm, encouraging, and direct. Avoid jargon. Be specific with numbers. "
        "Always prioritize high-interest debt elimination and building a small emergency fund "
        "before investing. Use the 50/30/20 framework as a starting point but adapt to the "
        "client's actual situation.\n\n"
        "You have three tools to call:\n"
        "1. save_executive_summary — call once with a 2-3 paragraph overview\n"
        "2. save_recommendations — call once with 5-8 prioritized action items\n"
        "3. save_monthly_plan — call once per month (plan 3-6 months ahead)\n\n"
        "Call all three tool types before calling submit_result."
    )
    MAX_TOKENS = 8192
    MAX_ITERATIONS = 25

    @property
    def tools(self) -> list[dict]:
        return [SUMMARY_TOOL, RECOMMENDATIONS_TOOL, MONTHLY_PLAN_TOOL]

    def _handle_tool(self, name: str, inputs: dict) -> Any:
        if name == "save_executive_summary":
            self._store["executive_summary"] = inputs["summary"]
            return {"status": "saved"}
        if name == "save_recommendations":
            self._store["recommendations"] = inputs["recommendations"]
            return {"status": "saved", "count": len(inputs["recommendations"])}
        if name == "save_monthly_plan":
            self._store.setdefault("monthly_plans", []).append(inputs)
            return {"status": "saved", "month": inputs["month"]}
        raise NotImplementedError(f"Unhandled tool: {name}")

    def run_planning(
        self,
        snapshot: FinancialSnapshot,
        avalanche: DebtPayoffPlan | None,
        snowball: DebtPayoffPlan | None,
        budget: BudgetPlan | None,
    ) -> tuple[str, list[str], list[MonthlyActionPlan]]:
        """Generate executive summary, recommendations, and monthly plans."""
        self._store = {}

        context = {
            "financial_snapshot": {
                "total_liquid_assets": snapshot.total_liquid_assets,
                "total_credit_card_debt": snapshot.total_credit_card_debt,
                "avg_monthly_income": snapshot.total_monthly_income,
                "avg_monthly_expenses": snapshot.total_monthly_expenses,
                "net_monthly_cash_flow": snapshot.net_monthly_cash_flow,
                "analysis_period": f"{snapshot.analysis_period_start} to {snapshot.analysis_period_end}",
                "credit_cards": [
                    {
                        "name": cc.account_name,
                        "balance": cc.current_balance,
                        "apr": f"{cc.annual_interest_rate*100:.2f}%",
                        "minimum_payment": cc.minimum_payment,
                    }
                    for cc in snapshot.credit_cards
                ],
                "spending_by_category": [
                    {
                        "category": s.category.value,
                        "monthly_average": s.monthly_average,
                        "percentage": s.percentage_of_spending,
                    }
                    for s in snapshot.spending_by_category
                ],
            }
        }

        if avalanche:
            context["avalanche_plan"] = {
                "months_to_payoff": avalanche.total_months,
                "total_interest_paid": avalanche.total_interest_paid,
                "monthly_budget": avalanche.monthly_payment_budget,
                "payoff_order": avalanche.payoff_order,
            }

        if snowball:
            context["snowball_plan"] = {
                "months_to_payoff": snowball.total_months,
                "total_interest_paid": snowball.total_interest_paid,
                "monthly_budget": snowball.monthly_payment_budget,
                "payoff_order": snowball.payoff_order,
            }

        if budget:
            context["budget_analysis"] = {
                "framework": budget.framework,
                "monthly_income": budget.monthly_income,
                "needs": {"target": budget.needs_target, "current": budget.current_needs},
                "wants": {"target": budget.wants_target, "current": budget.current_wants},
                "savings_debt": {"target": budget.savings_debt_target, "current": budget.current_savings_debt},
                "surplus_or_deficit": budget.surplus_or_deficit,
            }

        prompt = (
            "Here is my client's complete financial situation. Please:\n"
            "1. Call save_executive_summary with a personalized 2-3 paragraph assessment\n"
            "2. Call save_recommendations with 5-8 prioritized, specific action items\n"
            "3. Call save_monthly_plan 3-6 times to create a month-by-month action plan\n"
            "Then call submit_result with an empty object {}.\n\n"
            f"```json\n{json.dumps(context, indent=2)}\n```"
        )

        super().run(prompt)

        executive_summary = self._store.get("executive_summary", "")
        recommendations = self._store.get("recommendations", [])

        monthly_action_plans: list[MonthlyActionPlan] = []
        for plan_data in self._store.get("monthly_plans", []):
            monthly_action_plans.append(MonthlyActionPlan(
                month=plan_data.get("month", ""),
                priority_actions=plan_data.get("priority_actions", []),
                debt_payments=plan_data.get("debt_payments", {}),
                savings_target=float(plan_data.get("savings_target", 0.0)),
                budget_targets=plan_data.get("budget_targets", {}),
                key_milestones=plan_data.get("key_milestones", []),
            ))

        return executive_summary, recommendations, monthly_action_plans
