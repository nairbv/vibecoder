"""BaseClient ABC for the next-generation provider abstraction.

A Client is the new analogue of vibecoder.agents.agent.BaseAgent. It
wraps a single provider's "latest" API (OpenAI Responses, Anthropic
Messages, Gemini generate_content, etc.) and exposes a uniform async
iterator interface that the TUI consumes.

Compared to BaseAgent:
- History is stored in the canonical ClientMessage form, not the
  provider's wire format. This lets callers swap providers without
  losing context.
- Reasoning, server-side tools, and multimodal inputs are first-class.
- Token usage is reported via the Usage struct, including cache and
  reasoning token counts where the provider exposes them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Optional

from vibecoder.clients.messages import (
    ClientMessage,
    UserFile,
    UserImage,
    UserText,
)
from vibecoder.tools.base import Tool


class BaseClient(ABC):
    """Provider-neutral client interface.

    Subclasses implement `_run_turn` which performs one round-trip with
    the provider, yielding ClientMessage objects as they are produced.
    `ask` wraps `_run_turn` to handle the local-tool-call loop: when
    the assistant emits a ToolCall, the client executes the matching
    Tool, appends a ToolOutput to history, and continues until the
    assistant produces no further tool calls.
    """

    def __init__(
        self,
        system_prompt: str = "",
        tools: Optional[Dict[str, Tool]] = None,
        model: str = "",
        history: Optional[list[ClientMessage]] = None,
        # Provider-agnostic capability flags. Subclasses ignore flags
        # they do not support; cross-provider portability requires
        # callers to set the same flags on the new client when
        # switching providers.
        reasoning: Optional[str] = None,  # "low" | "medium" | "high" | None
        enable_web_search: bool = False,
    ):
        self.system_prompt = system_prompt
        self.tools: Dict[str, Tool] = tools or {}
        self.model = model
        self.history: list[ClientMessage] = list(history or [])
        self.reasoning = reasoning
        self.enable_web_search = enable_web_search

    def set_model(self, model: str) -> None:
        self.model = model

    # --- Public API ---

    async def ask(
        self,
        user_input: str | ClientMessage | list[ClientMessage],
    ) -> AsyncIterator[ClientMessage]:
        """Send a user turn and stream out assistant messages.

        `user_input` may be:
        - a plain string -> wrapped as UserText
        - a single user-part ClientMessage (UserText/UserImage/UserFile)
        - a list of user-part ClientMessages (multimodal turn)

        Yields TextOutput, Reasoning, ToolCall, ToolOutput,
        ServerToolUse, ServerToolResult instances. Each yielded message
        is also appended to `self.history` in order.
        """
        for part in self._normalize_input(user_input):
            self.history.append(part)

        # Loop until the assistant produces no local tool calls.
        while True:
            had_local_tool_call = False
            async for msg in self._run_turn():
                self.history.append(msg)
                yield msg
                # Local tool execution: subclasses yield ToolCall but
                # do not execute. We execute here to keep that logic
                # provider-agnostic.
                from vibecoder.clients.messages import ToolCall, ToolOutput

                if isinstance(msg, ToolCall):
                    had_local_tool_call = True
                    output = await self._execute_tool(msg)
                    self.history.append(output)
                    yield output
            if not had_local_tool_call:
                break

    # --- Subclass hooks ---

    @abstractmethod
    async def _run_turn(self) -> AsyncIterator[ClientMessage]:
        """Perform one provider round-trip using current self.history.

        Must yield assistant-side messages (TextOutput, Reasoning,
        ToolCall, ServerToolUse, ServerToolResult). Must not append to
        history; the caller (ask) handles that. Must not execute local
        tools; ask() handles that too.
        """
        raise NotImplementedError
        yield  # pragma: no cover

    # --- Helpers ---

    @staticmethod
    def _normalize_input(
        user_input: str | ClientMessage | list[ClientMessage],
    ) -> list[ClientMessage]:
        if isinstance(user_input, str):
            return [UserText(content=user_input)]
        if isinstance(user_input, ClientMessage):
            return [user_input]
        if isinstance(user_input, list):
            for p in user_input:
                if not isinstance(p, (UserText, UserImage, UserFile)):
                    raise TypeError(
                        f"ask() input list must contain only user-part "
                        f"ClientMessages; got {type(p).__name__}"
                    )
            return list(user_input)
        raise TypeError(
            f"ask() input must be str | ClientMessage | list[ClientMessage]; "
            f"got {type(user_input).__name__}"
        )

    async def _execute_tool(self, call):
        """Execute a local Tool and return a ToolOutput message.

        Bridges the canonical ClientMessage tool model to the existing
        Tool.run(ToolUse) -> ToolResult contract.
        """
        from vibecoder.clients.messages import ToolOutput
        from vibecoder.messages import ToolUse  # legacy

        if call.tool_name not in self.tools:
            return ToolOutput(
                tool_name=call.tool_name,
                tool_call_id=call.tool_call_id,
                content=(
                    f"[Tool {call.tool_name} not implemented] "
                    f"Available: {', '.join(self.tools.keys())}"
                ),
                is_error=True,
            )
        legacy_use = ToolUse(
            tool_name=call.tool_name,
            tool_call_id=call.tool_call_id,
            arguments=call.arguments,
        )
        try:
            legacy_result = await self.tools[call.tool_name].run(legacy_use)
        except Exception as e:  # pragma: no cover - best-effort guard
            return ToolOutput(
                tool_name=call.tool_name,
                tool_call_id=call.tool_call_id,
                content=f"[Tool {call.tool_name} raised {type(e).__name__}: {e}]",
                is_error=True,
            )
        return ToolOutput(
            tool_name=call.tool_name,
            tool_call_id=call.tool_call_id,
            content=getattr(legacy_result, "content", str(legacy_result)),
        )
