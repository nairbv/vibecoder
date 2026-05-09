"""Anthropic Messages API client.

Uses `client.messages.create` with first-class support for extended
thinking, server-side web search, and tool use. Constructor-injects
the SDK client (`anthropic.AsyncAnthropic` or compatible) for tests.
"""

from __future__ import annotations

import base64
from typing import Any, AsyncIterator, Dict, Optional

from vibecoder.clients.base import BaseClient
from vibecoder.clients.messages import (
    ClientMessage,
    Reasoning,
    ServerToolResult,
    ServerToolUse,
    TextOutput,
    ToolCall,
    ToolOutput,
    Usage,
    UserFile,
    UserImage,
    UserText,
)
from vibecoder.tools.base import Tool


def _g(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


_REASONING_BUDGET = {"low": 1024, "medium": 4096, "high": 16000}


class AnthropicClient(BaseClient):
    def __init__(
        self,
        client,
        system_prompt: str = "",
        tools: Optional[Dict[str, Tool]] = None,
        model: str = "claude-sonnet-4-6",
        history: Optional[list[ClientMessage]] = None,
        reasoning: Optional[str] = None,
        enable_web_search: bool = False,
        max_tokens: int = 4096,
    ):
        super().__init__(
            system_prompt=system_prompt,
            tools=tools,
            model=model,
            history=history,
            reasoning=reasoning,
            enable_web_search=enable_web_search,
        )
        self.client = client
        self.max_tokens = max_tokens

    # --- Schema conversion ---

    def _convert_tools(self) -> list[dict]:
        out: list[dict] = []
        for tool in self.tools.values():
            schema = tool.canonical_schema
            params = schema.get("parameters", {"type": "object", "properties": {}})
            out.append(
                {
                    "name": schema["name"],
                    "description": schema.get("description", ""),
                    "input_schema": params,
                }
            )
        if self.enable_web_search:
            out.append(
                {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
            )
        return out

    # --- History -> messages list ---

    def _build_messages(self) -> list[dict]:
        """Group consecutive same-role canonical messages into Anthropic
        message turns with content-block lists.
        """
        turns: list[dict] = []
        current_role: Optional[str] = None
        current_blocks: list[dict] = []

        def flush():
            if current_role is not None and current_blocks:
                turns.append({"role": current_role, "content": list(current_blocks)})

        for msg in self.history:
            role, block = self._message_to_block(msg)
            if block is None:
                continue
            if role != current_role:
                flush()
                current_role = role
                current_blocks = [block]
            else:
                current_blocks.append(block)
        # flush tail
        if current_role is not None and current_blocks:
            turns.append({"role": current_role, "content": list(current_blocks)})
        return turns

    def _message_to_block(self, msg: ClientMessage):
        if isinstance(msg, UserText):
            return "user", {"type": "text", "text": msg.content}
        if isinstance(msg, UserImage):
            if msg.url:
                return "user", {
                    "type": "image",
                    "source": {"type": "url", "url": msg.url},
                }
            if msg.data and msg.media_type:
                b64 = base64.b64encode(msg.data).decode("ascii")
                return "user", {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": msg.media_type,
                        "data": b64,
                    },
                }
            return "user", None
        if isinstance(msg, UserFile):
            if msg.url:
                return "user", {
                    "type": "document",
                    "source": {"type": "url", "url": msg.url},
                }
            if msg.data and msg.media_type:
                b64 = base64.b64encode(msg.data).decode("ascii")
                return "user", {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": msg.media_type,
                        "data": b64,
                    },
                }
            return "user", None
        if isinstance(msg, TextOutput):
            return "assistant", {"type": "text", "text": msg.content}
        if isinstance(msg, Reasoning):
            if msg.redacted:
                return "assistant", {
                    "type": "redacted_thinking",
                    "data": msg.encrypted_content or "",
                }
            if msg.signature is None:
                # Without signature, Anthropic rejects re-submitted thinking.
                # Drop on history rebuild.
                return "assistant", None
            return "assistant", {
                "type": "thinking",
                "thinking": msg.content,
                "signature": msg.signature,
            }
        if isinstance(msg, ToolCall):
            return "assistant", {
                "type": "tool_use",
                "id": msg.tool_call_id,
                "name": msg.tool_name,
                "input": msg.arguments,
            }
        if isinstance(msg, ToolOutput):
            return "user", {
                "type": "tool_result",
                "tool_use_id": msg.tool_call_id,
                "content": msg.content,
                **({"is_error": True} if msg.is_error else {}),
            }
        # Server-side tool messages re-submitted as-is is provider-
        # internal and not generally needed; skip.
        if isinstance(msg, (ServerToolUse, ServerToolResult)):
            return "assistant", None
        return None, None

    # --- Provider call ---

    async def _run_turn(self) -> AsyncIterator[ClientMessage]:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": self._build_messages(),
            "max_tokens": self.max_tokens,
        }
        if self.system_prompt:
            kwargs["system"] = self.system_prompt
        tools = self._convert_tools()
        if tools:
            kwargs["tools"] = tools
        if self.reasoning and self.reasoning in _REASONING_BUDGET:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": _REASONING_BUDGET[self.reasoning],
            }

        response = await self.client.messages.create(**kwargs)

        usage = self._extract_usage(_g(response, "usage"))
        produced: list[ClientMessage] = []
        for block in _g(response, "content", []) or []:
            for parsed in self._parse_block(block):
                produced.append(parsed)
        if produced and usage is not None:
            produced[-1].usage = usage
        for msg in produced:
            yield msg

    def _parse_block(self, block: Any) -> list[ClientMessage]:
        btype = _g(block, "type")
        if btype == "text":
            return [TextOutput(content=_g(block, "text", ""))]
        if btype == "thinking":
            return [
                Reasoning(
                    content=_g(block, "thinking", "") or "",
                    signature=_g(block, "signature"),
                )
            ]
        if btype == "redacted_thinking":
            return [
                Reasoning(
                    content="",
                    encrypted_content=_g(block, "data"),
                    redacted=True,
                )
            ]
        if btype == "tool_use":
            return [
                ToolCall(
                    tool_name=_g(block, "name", ""),
                    tool_call_id=_g(block, "id", ""),
                    arguments=_g(block, "input", {}) or {},
                )
            ]
        if btype == "server_tool_use":
            return [
                ServerToolUse(
                    tool_name=_g(block, "name", ""),
                    tool_call_id=_g(block, "id", ""),
                    arguments=_g(block, "input", {}) or {},
                )
            ]
        if btype == "web_search_tool_result":
            content = _g(block, "content")
            return [
                ServerToolResult(
                    tool_name="web_search",
                    tool_call_id=_g(block, "tool_use_id", ""),
                    content=str(content) if content is not None else "",
                )
            ]
        return []

    @staticmethod
    def _extract_usage(usage_obj: Any) -> Optional[Usage]:
        if usage_obj is None:
            return None
        return Usage(
            input_tokens=_g(usage_obj, "input_tokens", 0) or 0,
            output_tokens=_g(usage_obj, "output_tokens", 0) or 0,
            cache_read_tokens=_g(usage_obj, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=_g(usage_obj, "cache_creation_input_tokens", 0) or 0,
        )
