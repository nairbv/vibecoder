"""Gemini client using google-genai's async surface.

Calls `client.aio.models.generate_content(...)` and parses the
response's first candidate. Supports thinking, function calling,
google_search server tool, and multimodal user input.
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


class GeminiClient(BaseClient):
    def __init__(
        self,
        client,
        system_prompt: str = "",
        tools: Optional[Dict[str, Tool]] = None,
        model: str = "gemini-2.5-flash",
        history: Optional[list[ClientMessage]] = None,
        reasoning: Optional[str] = None,
        enable_web_search: bool = False,
        max_output_tokens: Optional[int] = None,
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
        self.max_output_tokens = max_output_tokens

    # --- Schema conversion ---

    def _convert_tools(self) -> list[dict]:
        out: list[dict] = []
        function_decls: list[dict] = []
        for tool in self.tools.values():
            schema = tool.canonical_schema
            function_decls.append(
                {
                    "name": schema["name"],
                    "description": schema.get("description", ""),
                    "parameters": schema.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                }
            )
        if function_decls:
            out.append({"function_declarations": function_decls})
        if self.enable_web_search:
            out.append({"google_search": {}})
        return out

    # --- History -> contents list ---

    def _build_contents(self) -> list[dict]:
        contents: list[dict] = []
        current_role: Optional[str] = None
        current_parts: list[dict] = []

        def flush():
            if current_role is not None and current_parts:
                contents.append({"role": current_role, "parts": list(current_parts)})

        for msg in self.history:
            role, part = self._message_to_part(msg)
            if part is None:
                continue
            if role != current_role:
                flush()
                current_role = role
                current_parts = [part]
            else:
                current_parts.append(part)
        if current_role is not None and current_parts:
            contents.append({"role": current_role, "parts": list(current_parts)})
        return contents

    def _message_to_part(self, msg: ClientMessage):
        if isinstance(msg, UserText):
            return "user", {"text": msg.content}
        if isinstance(msg, UserImage):
            if msg.url:
                return "user", {
                    "file_data": {
                        "file_uri": msg.url,
                        "mime_type": msg.media_type or "image/png",
                    }
                }
            if msg.data and msg.media_type:
                b64 = base64.b64encode(msg.data).decode("ascii")
                return "user", {
                    "inline_data": {"mime_type": msg.media_type, "data": b64}
                }
            return "user", None
        if isinstance(msg, UserFile):
            if msg.url:
                return "user", {
                    "file_data": {
                        "file_uri": msg.url,
                        "mime_type": msg.media_type or "application/octet-stream",
                    }
                }
            if msg.data and msg.media_type:
                b64 = base64.b64encode(msg.data).decode("ascii")
                return "user", {
                    "inline_data": {"mime_type": msg.media_type, "data": b64}
                }
            return "user", None
        if isinstance(msg, TextOutput):
            return "model", {"text": msg.content}
        if isinstance(msg, Reasoning):
            # Gemini does not accept thought parts back as input; drop.
            return "model", None
        if isinstance(msg, ToolCall):
            return "model", {
                "function_call": {"name": msg.tool_name, "args": msg.arguments}
            }
        if isinstance(msg, ToolOutput):
            return "user", {
                "function_response": {
                    "name": msg.tool_name,
                    "response": {"result": msg.content},
                }
            }
        if isinstance(msg, (ServerToolUse, ServerToolResult)):
            return "model", None
        return None, None

    # --- Provider call ---

    async def _run_turn(self) -> AsyncIterator[ClientMessage]:
        config: Dict[str, Any] = {}
        if self.system_prompt:
            config["system_instruction"] = self.system_prompt
        tools = self._convert_tools()
        if tools:
            config["tools"] = tools
        if self.reasoning and self.reasoning in _REASONING_BUDGET:
            config["thinking_config"] = {
                "include_thoughts": True,
                "thinking_budget": _REASONING_BUDGET[self.reasoning],
            }
        if self.max_output_tokens is not None:
            config["max_output_tokens"] = self.max_output_tokens

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=self._build_contents(),
            config=config or None,
        )

        usage = self._extract_usage(_g(response, "usage_metadata"))
        produced: list[ClientMessage] = []
        candidates = _g(response, "candidates", []) or []
        if candidates:
            content = _g(candidates[0], "content")
            for part in _g(content, "parts", []) or []:
                for parsed in self._parse_part(part):
                    produced.append(parsed)
        if produced and usage is not None:
            produced[-1].usage = usage
        for msg in produced:
            yield msg

    def _parse_part(self, part: Any) -> list[ClientMessage]:
        text = _g(part, "text")
        is_thought = bool(_g(part, "thought"))
        function_call = _g(part, "function_call")
        if function_call is not None:
            name = _g(function_call, "name", "") or ""
            args = _g(function_call, "args", {}) or {}
            call_id = _g(part, "function_call_id") or _g(function_call, "id") or name
            return [
                ToolCall(
                    tool_name=name,
                    tool_call_id=call_id,
                    arguments=dict(args) if not isinstance(args, dict) else args,
                )
            ]
        if text is not None:
            if is_thought:
                return [Reasoning(content=text)]
            return [TextOutput(content=text)]
        return []

    @staticmethod
    def _extract_usage(usage_obj: Any) -> Optional[Usage]:
        if usage_obj is None:
            return None
        return Usage(
            input_tokens=_g(usage_obj, "prompt_token_count", 0) or 0,
            output_tokens=_g(usage_obj, "candidates_token_count", 0) or 0,
            cache_read_tokens=_g(usage_obj, "cached_content_token_count", 0) or 0,
            reasoning_tokens=_g(usage_obj, "thoughts_token_count", 0) or 0,
        )
