"""History portability across providers.

Switching `/provider` mid-session must keep canonical history usable.
We construct a representative canonical history (user text, assistant
text, tool call, tool output, multimodal user input) and assert that
each provider client serializes it through `_build_*` without raising
and emits the expected role/turn structure.

We also exercise reasoning conversion edge cases:
- OpenAI requires a `provider_id` to round-trip a Reasoning item;
  without it, the message is dropped on rebuild.
- Anthropic requires a `signature` to round-trip a thinking block;
  without it, drop.
- Gemini does not accept thought parts back as input, so any
  Reasoning is dropped.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vibecoder.clients import (
    AnthropicClient,
    GeminiClient,
    OpenAIClient,
    Reasoning,
    TextOutput,
    ToolCall,
    ToolOutput,
    UserImage,
    UserText,
)

from .conftest import ns


def make_canonical_history() -> list:
    return [
        UserText(content="hello"),
        TextOutput(content="hi! what do you need?"),
        UserText(content="run the fake tool"),
        ToolCall(tool_name="fake_tool", tool_call_id="call_1", arguments={"x": "v"}),
        ToolOutput(tool_name="fake_tool", tool_call_id="call_1", content="result text"),
        TextOutput(content="done"),
        UserImage(data=b"\x89PNG", media_type="image/png"),
    ]


@pytest.mark.asyncio
async def test_openai_round_trips_history():
    response = ns(
        output=[ns(type="message", content=[ns(type="output_text", text="ok")])],
        usage=None,
    )
    client = AsyncMock()
    client.responses.create = AsyncMock(return_value=response)
    c = OpenAIClient(client=client, history=make_canonical_history())
    [m async for m in c.ask("next")]
    items = client.responses.create.call_args.kwargs["input"]
    types = [item.get("type") or item.get("role") for item in items]
    # User turns and assistant turns are separate items
    assert "user" in types
    assert "assistant" in types
    assert "function_call" in types
    assert "function_call_output" in types


@pytest.mark.asyncio
async def test_anthropic_round_trips_history():
    response = ns(content=[ns(type="text", text="ok")], usage=None)
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=response)
    c = AnthropicClient(client=client, history=make_canonical_history())
    [m async for m in c.ask("next")]
    messages = client.messages.create.call_args.kwargs["messages"]
    flat_types = []
    for turn in messages:
        for block in turn["content"]:
            flat_types.append(block["type"])
    assert "text" in flat_types
    assert "tool_use" in flat_types
    assert "tool_result" in flat_types
    assert "image" in flat_types


@pytest.mark.asyncio
async def test_gemini_round_trips_history():
    response = ns(
        candidates=[
            ns(content=ns(parts=[ns(text="ok", thought=False, function_call=None)]))
        ],
        usage_metadata=None,
    )
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=response)
    c = GeminiClient(client=client, history=make_canonical_history())
    [m async for m in c.ask("next")]
    contents = client.aio.models.generate_content.call_args.kwargs["contents"]
    keys = []
    for content in contents:
        for part in content["parts"]:
            keys.extend(part.keys())
    assert "text" in keys
    assert "function_call" in keys
    assert "function_response" in keys
    assert "inline_data" in keys


@pytest.mark.asyncio
async def test_reasoning_dropped_when_unprintable():
    """Reasoning without provider-specific pass-through is dropped on
    rebuild. This is the defined behavior — providers reject signed
    thinking that cannot be verified.
    """
    history = [
        UserText(content="q"),
        Reasoning(content="thinking"),  # no signature, no provider_id
        TextOutput(content="a"),
    ]
    # OpenAI: dropped (no provider_id)
    response = ns(
        output=[ns(type="message", content=[ns(type="output_text", text="ok")])],
        usage=None,
    )
    client = AsyncMock()
    client.responses.create = AsyncMock(return_value=response)
    c = OpenAIClient(client=client, history=history)
    [m async for m in c.ask("again")]
    items = client.responses.create.call_args.kwargs["input"]
    assert not any(item.get("type") == "reasoning" for item in items)

    # Anthropic: dropped (no signature)
    a_response = ns(content=[ns(type="text", text="ok")], usage=None)
    a_client = AsyncMock()
    a_client.messages.create = AsyncMock(return_value=a_response)
    ac = AnthropicClient(client=a_client, history=history)
    [m async for m in ac.ask("again")]
    a_messages = a_client.messages.create.call_args.kwargs["messages"]
    flat = []
    for turn in a_messages:
        for block in turn["content"]:
            flat.append(block["type"])
    assert "thinking" not in flat
    assert "redacted_thinking" not in flat


@pytest.mark.asyncio
async def test_reasoning_with_provider_id_kept_on_openai():
    history = [
        UserText(content="q"),
        Reasoning(content="thinking", provider_id="rs_1", encrypted_content="opaque"),
        TextOutput(content="a"),
    ]
    response = ns(
        output=[ns(type="message", content=[ns(type="output_text", text="ok")])],
        usage=None,
    )
    client = AsyncMock()
    client.responses.create = AsyncMock(return_value=response)
    c = OpenAIClient(client=client, history=history)
    [m async for m in c.ask("again")]
    items = client.responses.create.call_args.kwargs["input"]
    reasoning_items = [item for item in items if item.get("type") == "reasoning"]
    assert len(reasoning_items) == 1
    assert reasoning_items[0]["id"] == "rs_1"
    assert reasoning_items[0]["encrypted_content"] == "opaque"


@pytest.mark.asyncio
async def test_reasoning_with_signature_kept_on_anthropic():
    history = [
        UserText(content="q"),
        Reasoning(content="thinking", signature="sig"),
        TextOutput(content="a"),
    ]
    response = ns(content=[ns(type="text", text="ok")], usage=None)
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=response)
    c = AnthropicClient(client=client, history=history)
    [m async for m in c.ask("again")]
    messages = client.messages.create.call_args.kwargs["messages"]
    thinking = []
    for turn in messages:
        for block in turn["content"]:
            if block["type"] == "thinking":
                thinking.append(block)
    assert len(thinking) == 1
    assert thinking[0]["signature"] == "sig"
