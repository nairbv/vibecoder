"""Shared test helpers for client tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from vibecoder.messages import ToolResult, ToolUse
from vibecoder.tools.base import Tool


def ns(**kwargs: Any) -> SimpleNamespace:
    """Build a SimpleNamespace recursively from kwargs.

    Lets tests construct objects that look like provider SDK return
    values (attribute access) without instantiating real SDK types.
    """
    return SimpleNamespace(**kwargs)


class FakeTool(Tool):
    """A minimal Tool used by client tests.

    Captures the last invocation and returns a canned result.
    """

    name = "fake_tool"

    def __init__(self, result: str = "fake result"):
        self._result = result
        self.last_call: ToolUse | None = None

    @property
    def prompt_description(self) -> str:
        return "A fake tool for tests."

    @property
    def signature(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "fake_tool",
                "description": "Does fake things.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "string"},
                    },
                    "required": ["x"],
                },
            },
        }

    async def run(self, tool_use: ToolUse) -> ToolResult:
        self.last_call = tool_use
        return ToolResult(
            content=self._result,
            tool_name=self.name,
            tool_call_id=tool_use.tool_call_id,
        )


@pytest.fixture
def fake_tool():
    return FakeTool()
