"""vibecoder.clients — provider-neutral client abstraction.

Companion to vibecoder.agents (legacy, kept for downstream lib users).
New code should target this module. The TUI will be migrated in a
follow-up.

Public surface:
    BaseClient — ABC for provider clients
    OpenAIClient, AnthropicClient, GeminiClient, MockClient
    create_client(provider, ...) — factory
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from vibecoder.clients.anthropic import AnthropicClient
from vibecoder.clients.base import BaseClient
from vibecoder.clients.gemini import GeminiClient
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
from vibecoder.clients.mock import MockClient
from vibecoder.clients.openai import OpenAIClient

__all__ = [
    "BaseClient",
    "OpenAIClient",
    "AnthropicClient",
    "GeminiClient",
    "MockClient",
    "ClientMessage",
    "UserText",
    "UserImage",
    "UserFile",
    "TextOutput",
    "Reasoning",
    "ToolCall",
    "ToolOutput",
    "ServerToolUse",
    "ServerToolResult",
    "Usage",
    "create_client",
]


def create_client(
    provider: str,
    *,
    sdk_client: Any = None,
    system_prompt: str = "",
    tools: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    history: Optional[list[ClientMessage]] = None,
    reasoning: Optional[str] = None,
    enable_web_search: bool = False,
    **provider_kwargs,
) -> BaseClient:
    """Factory for clients by provider name.

    `provider` is one of: "openai", "anthropic", "gemini", "mock".
    `sdk_client` is the provider SDK instance (AsyncOpenAI,
    AsyncAnthropic, genai.Client, ...). For "mock" it's ignored;
    pass `provider_kwargs={"scripts": ...}` instead.
    """
    common = dict(
        system_prompt=system_prompt,
        tools=tools,
        history=history,
        reasoning=reasoning,
        enable_web_search=enable_web_search,
    )
    if model is not None:
        common["model"] = model

    if provider == "openai":
        return OpenAIClient(client=sdk_client, **common, **provider_kwargs)
    if provider == "anthropic":
        return AnthropicClient(client=sdk_client, **common, **provider_kwargs)
    if provider == "gemini":
        return GeminiClient(client=sdk_client, **common, **provider_kwargs)
    if provider == "mock":
        return MockClient(**common, **provider_kwargs)
    raise ValueError(f"Unknown provider: {provider!r}")
