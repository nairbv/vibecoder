"""Tests for AnthropicClient against a mocked Messages API client."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from vibecoder.clients import (
    AnthropicClient,
    Reasoning,
    ServerToolResult,
    ServerToolUse,
    TextOutput,
    ToolCall,
    ToolOutput,
    UserImage,
    UserText,
)

from .conftest import ns


def _mock_client(response):
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=response)
    return client


def _resp(content_blocks, usage=None):
    return ns(content=content_blocks, usage=usage)


@pytest.mark.asyncio
async def test_text_response_parsed():
    response = _resp(
        [ns(type="text", text="hi there")],
        usage=ns(input_tokens=5, output_tokens=2),
    )
    client = _mock_client(response)
    c = AnthropicClient(client=client)
    out = [m async for m in c.ask("hi")]
    assert isinstance(out[0], TextOutput)
    assert out[0].content == "hi there"
    assert out[0].usage.input_tokens == 5


@pytest.mark.asyncio
async def test_thinking_block_parsed():
    response = _resp(
        [
            ns(type="thinking", thinking="reasoning...", signature="sig"),
            ns(type="text", text="answer"),
        ],
        usage=ns(input_tokens=10, output_tokens=4, cache_read_input_tokens=2),
    )
    client = _mock_client(response)
    c = AnthropicClient(client=client, reasoning="medium")
    out = [m async for m in c.ask("hi")]
    assert isinstance(out[0], Reasoning)
    assert out[0].signature == "sig"
    assert isinstance(out[1], TextOutput)
    assert out[1].usage.cache_read_tokens == 2


@pytest.mark.asyncio
async def test_thinking_config_in_request():
    response = _resp([ns(type="text", text="ok")])
    client = _mock_client(response)
    c = AnthropicClient(client=client, reasoning="high")
    [m async for m in c.ask("hi")]
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["thinking"]["type"] == "enabled"
    assert kwargs["thinking"]["budget_tokens"] >= 1024


@pytest.mark.asyncio
async def test_tool_use_executes_local_tool(fake_tool):
    first = _resp(
        [
            ns(
                type="tool_use",
                id="toolu_1",
                name="fake_tool",
                input={"x": "v"},
            )
        ]
    )
    second = _resp([ns(type="text", text="done")])
    client = AsyncMock()
    client.messages.create = AsyncMock(side_effect=[first, second])
    c = AnthropicClient(client=client, tools={"fake_tool": fake_tool})
    out = [m async for m in c.ask("go")]
    assert isinstance(out[0], ToolCall)
    assert isinstance(out[1], ToolOutput)
    assert out[1].content == "fake result"
    assert isinstance(out[2], TextOutput)
    # Verify second call's `messages` includes the tool_use and tool_result
    second_kwargs = client.messages.create.call_args_list[1].kwargs
    types = []
    for turn in second_kwargs["messages"]:
        for block in turn["content"]:
            types.append(block["type"])
    assert "tool_use" in types
    assert "tool_result" in types


@pytest.mark.asyncio
async def test_request_shape_for_tools_and_system():
    response = _resp([ns(type="text", text="ok")])
    client = _mock_client(response)
    c = AnthropicClient(
        client=client,
        system_prompt="be helpful",
        enable_web_search=True,
    )
    [m async for m in c.ask("hi")]
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["system"] == "be helpful"
    tool_types = [t.get("type") for t in kwargs["tools"]]
    assert "web_search_20250305" in tool_types


@pytest.mark.asyncio
async def test_local_tool_uses_anthropic_input_schema(fake_tool):
    response = _resp([ns(type="text", text="ok")])
    client = _mock_client(response)
    c = AnthropicClient(client=client, tools={"fake_tool": fake_tool})
    [m async for m in c.ask("hi")]
    kwargs = client.messages.create.call_args.kwargs
    local = [t for t in kwargs["tools"] if t.get("name") == "fake_tool"]
    assert len(local) == 1
    assert "input_schema" in local[0]
    assert "x" in local[0]["input_schema"]["properties"]


@pytest.mark.asyncio
async def test_user_image_inline_data():
    response = _resp([ns(type="text", text="ok")])
    client = _mock_client(response)
    c = AnthropicClient(client=client)
    [
        m
        async for m in c.ask(
            [
                UserText(content="describe"),
                UserImage(data=b"\x89PNG", media_type="image/png"),
            ]
        )
    ]
    kwargs = client.messages.create.call_args.kwargs
    user_turn = kwargs["messages"][0]
    block_types = [b["type"] for b in user_turn["content"]]
    assert "text" in block_types
    assert "image" in block_types


@pytest.mark.asyncio
async def test_server_tool_use_yields_messages():
    response = _resp(
        [
            ns(
                type="server_tool_use",
                id="srv_1",
                name="web_search",
                input={"query": "x"},
            ),
            ns(
                type="web_search_tool_result",
                tool_use_id="srv_1",
                content=[{"type": "web_search_result", "title": "x"}],
            ),
            ns(type="text", text="found"),
        ]
    )
    client = _mock_client(response)
    c = AnthropicClient(client=client, enable_web_search=True)
    out = [m async for m in c.ask("search")]
    assert isinstance(out[0], ServerToolUse)
    assert isinstance(out[1], ServerToolResult)
    assert isinstance(out[2], TextOutput)


@pytest.mark.asyncio
async def test_consecutive_user_parts_grouped_into_one_turn():
    response = _resp([ns(type="text", text="ok")])
    client = _mock_client(response)
    c = AnthropicClient(client=client)
    # Two user parts in one ask call -> single user turn with two blocks
    [m async for m in c.ask([UserText(content="a"), UserText(content="b")])]
    kwargs = client.messages.create.call_args.kwargs
    assert len(kwargs["messages"]) == 1
    assert len(kwargs["messages"][0]["content"]) == 2
