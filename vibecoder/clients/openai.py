"""OpenAI Responses API client.

Uses the new Responses API (`client.responses.create`) rather than
Chat Completions. The Responses API natively supports reasoning items,
server-side tools (web_search, code_interpreter), and multimodal input
in a single unified shape.

The client is constructor-injected for testability. Pass an
`openai.AsyncOpenAI` (or compatible AsyncMock) instance.
"""

from __future__ import annotations

import json
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
    """Get attribute or dict key from SDK return values.

    Pydantic SDK objects support attribute access; AsyncMocks and
    plain-dict fixtures use mapping access. We try both.
    """
    if obj is None:
        return default
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


class OpenAIClient(BaseClient):
    def __init__(
        self,
        client,
        system_prompt: str = "",
        tools: Optional[Dict[str, Tool]] = None,
        model: str = "gpt-5-mini",
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

    def _convert_tools(self) -> Optional[list[dict]]:
        out: list[dict] = []
        for tool in self.tools.values():
            schema = tool.canonical_schema
            out.append(
                {
                    "type": "function",
                    "name": schema["name"],
                    "description": schema.get("description", ""),
                    "parameters": schema.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                }
            )
        if self.enable_web_search:
            out.append({"type": "web_search"})
        return out or None

    # --- History -> Responses `input` items ---

    def _build_input(self) -> list[dict]:
        items: list[dict] = []
        for msg in self.history:
            converted = self._message_to_input_item(msg)
            if converted is None:
                continue
            if isinstance(converted, list):
                items.extend(converted)
            else:
                items.append(converted)
        return items

    def _message_to_input_item(self, msg: ClientMessage):
        if isinstance(msg, UserText):
            return {
                "role": "user",
                "content": [{"type": "input_text", "text": msg.content}],
            }
        if isinstance(msg, UserImage):
            if msg.url:
                image_url = msg.url
            elif msg.data and msg.media_type:
                import base64

                b64 = base64.b64encode(msg.data).decode("ascii")
                image_url = f"data:{msg.media_type};base64,{b64}"
            else:
                return None
            return {
                "role": "user",
                "content": [{"type": "input_image", "image_url": image_url}],
            }
        if isinstance(msg, UserFile):
            if msg.url:
                return {
                    "role": "user",
                    "content": [{"type": "input_file", "file_url": msg.url}],
                }
            if msg.data and msg.filename:
                import base64

                b64 = base64.b64encode(msg.data).decode("ascii")
                return {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": msg.filename,
                            "file_data": (
                                f"data:{msg.media_type or 'application/octet-stream'};"
                                f"base64,{b64}"
                            ),
                        }
                    ],
                }
            return None
        if isinstance(msg, TextOutput):
            return {
                "role": "assistant",
                "content": [{"type": "output_text", "text": msg.content}],
            }
        if isinstance(msg, Reasoning):
            # Only round-trippable if we have the provider id.
            if not msg.provider_id:
                return None
            item: dict = {
                "type": "reasoning",
                "id": msg.provider_id,
                "summary": (
                    [{"type": "summary_text", "text": msg.content}]
                    if msg.content
                    else []
                ),
            }
            if msg.encrypted_content:
                item["encrypted_content"] = msg.encrypted_content
            return item
        if isinstance(msg, ToolCall):
            return {
                "type": "function_call",
                "call_id": msg.tool_call_id,
                "name": msg.tool_name,
                "arguments": json.dumps(msg.arguments),
            }
        if isinstance(msg, ToolOutput):
            return {
                "type": "function_call_output",
                "call_id": msg.tool_call_id,
                "output": msg.content,
            }
        # Server tool messages: pass-through is provider-internal; we
        # don't reconstruct on follow-up calls because the provider
        # references them by id from the same response. Skip on history
        # rebuild.
        if isinstance(msg, (ServerToolUse, ServerToolResult)):
            return None
        return None

    # --- Provider call ---

    async def _run_turn(self) -> AsyncIterator[ClientMessage]:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "input": self._build_input(),
        }
        if self.system_prompt:
            kwargs["instructions"] = self.system_prompt
        tools = self._convert_tools()
        if tools:
            kwargs["tools"] = tools
        if self.reasoning:
            kwargs["reasoning"] = {"effort": self.reasoning}
        if self.max_output_tokens is not None:
            kwargs["max_output_tokens"] = self.max_output_tokens

        response = await self.client.responses.create(**kwargs)

        usage = self._extract_usage(_g(response, "usage"))
        output_items = _g(response, "output", []) or []

        # Attach usage to the final yielded message of this turn so
        # callers can sum across turns. We collect and then yield in
        # order, marking the last with usage.
        produced: list[ClientMessage] = []
        for item in output_items:
            for parsed in self._parse_output_item(item):
                produced.append(parsed)
        if produced and usage is not None:
            produced[-1].usage = usage
        for msg in produced:
            yield msg

    def _parse_output_item(self, item: Any) -> list[ClientMessage]:
        item_type = _g(item, "type")
        if item_type == "message":
            results: list[ClientMessage] = []
            for content in _g(item, "content", []) or []:
                ctype = _g(content, "type")
                if ctype == "output_text":
                    results.append(TextOutput(content=_g(content, "text", "")))
            return results
        if item_type == "reasoning":
            summary_parts = _g(item, "summary", []) or []
            text = "\n".join(
                _g(p, "text", "")
                for p in summary_parts
                if _g(p, "type") == "summary_text"
            )
            return [
                Reasoning(
                    content=text,
                    provider_id=_g(item, "id"),
                    encrypted_content=_g(item, "encrypted_content"),
                )
            ]
        if item_type == "function_call":
            args_raw = _g(item, "arguments", "") or ""
            try:
                args = json.loads(args_raw) if args_raw else {}
            except json.JSONDecodeError:
                args = {"_raw": args_raw}
            return [
                ToolCall(
                    tool_name=_g(item, "name", ""),
                    tool_call_id=_g(item, "call_id", "") or _g(item, "id", ""),
                    arguments=args,
                )
            ]
        if item_type == "web_search_call":
            return [
                ServerToolUse(
                    tool_name="web_search",
                    tool_call_id=_g(item, "id", ""),
                    arguments=_g(item, "action", {}) or {},
                ),
                ServerToolResult(
                    tool_name="web_search",
                    tool_call_id=_g(item, "id", ""),
                    content=str(_g(item, "status", "")),
                ),
            ]
        return []

    @staticmethod
    def _extract_usage(usage_obj: Any) -> Optional[Usage]:
        if usage_obj is None:
            return None
        details = _g(usage_obj, "input_tokens_details") or _g(
            usage_obj, "prompt_tokens_details"
        )
        cache_read = _g(details, "cached_tokens", 0) or 0
        out_details = _g(usage_obj, "output_tokens_details")
        reasoning = _g(out_details, "reasoning_tokens", 0) or 0
        return Usage(
            input_tokens=_g(usage_obj, "input_tokens", 0)
            or _g(usage_obj, "prompt_tokens", 0)
            or 0,
            output_tokens=_g(usage_obj, "output_tokens", 0)
            or _g(usage_obj, "completion_tokens", 0)
            or 0,
            cache_read_tokens=cache_read,
            reasoning_tokens=reasoning,
        )
