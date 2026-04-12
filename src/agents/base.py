"""Base agent class — handles the Anthropic tool-use loop."""

from __future__ import annotations
import json
from typing import Any, Callable
import anthropic
from rich.console import Console
from rich.text import Text

from src.config import CLAUDE_MODEL

console = Console()


def _tool_def(
    name: str,
    description: str,
    properties: dict[str, dict],
    required: list[str],
) -> dict:
    """Build an Anthropic tool definition dict."""
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


SUBMIT_TOOL = _tool_def(
    name="submit_result",
    description="Call this when your work is complete. Pass the final structured result.",
    properties={
        "result": {
            "type": "object",
            "description": "The final result as a JSON object.",
        }
    },
    required=["result"],
)


class BaseAgent:
    """
    Base class for all agents.

    Subclasses must implement:
      - ``SYSTEM`` class-level string
      - ``tools`` property returning list of tool definitions
      - ``_handle_tool(name, inputs)`` for non-submit tools
    """

    SYSTEM: str = "You are a helpful AI agent."
    MODEL: str = CLAUDE_MODEL
    MAX_TOKENS: int = 4096
    MAX_ITERATIONS: int = 30

    def __init__(self, client: anthropic.Anthropic, agent_label: str = "agent"):
        self.client = client
        self.label = agent_label
        self._store: dict[str, Any] = {}  # internal scratch-pad for tool results

    # ── Public ────────────────────────────────────────────────────────────────

    def run(self, prompt: str) -> dict:
        """Run the agent with the given prompt and return the submitted result."""
        messages: list[dict] = [{"role": "user", "content": prompt}]
        tools = [*self.tools, SUBMIT_TOOL]

        for iteration in range(self.MAX_ITERATIONS):
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": self.SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
                tools=tools,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # No tool call — return any text content
                for block in response.content:
                    if hasattr(block, "text"):
                        return {"text": block.text}
                return {}

            # ── Process tool calls ─────────────────────────────────────────
            tool_results: list[dict] = []
            final_result: dict | None = None

            for block in response.content:
                if not hasattr(block, "type") or block.type != "tool_use":
                    continue

                if block.name == "submit_result":
                    final_result = block.input.get("result", block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"status": "accepted"}),
                        }
                    )
                else:
                    self._log_tool(block.name)
                    try:
                        result = self._handle_tool(block.name, block.input)
                    except Exception as exc:
                        result = {"error": str(exc)}
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        }
                    )

            if final_result is not None:
                return final_result

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        raise RuntimeError(f"{self.label}: exceeded {self.MAX_ITERATIONS} iterations")

    # ── Subclass interface ────────────────────────────────────────────────────

    @property
    def tools(self) -> list[dict]:
        return []

    def _handle_tool(self, name: str, inputs: dict) -> Any:
        raise NotImplementedError(f"Unhandled tool: {name}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log_tool(self, tool_name: str) -> None:
        t = Text()
        t.append(f"  {self.label}", style="bold cyan")
        t.append(" → ", style="dim")
        t.append(tool_name, style="yellow")
        console.print(t)
