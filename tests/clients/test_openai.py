"""Tests for OpenAIClient against a mocked Responses API client."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from vibecoder.clients import (
    OpenAIClient,
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
    client.responses.create = AsyncMock(return_value=response)
    return client


def _resp(output_items, usage=None):
    return ns(output=output_items, usage=usage)


@pytest.mark.asyncio
async def test_text_response_parsed():
    response = _resp(
        [
            ns(
                type="message",
                content=[ns(type="output_text", text="hello")],
            )
        ],
        usage=ns(input_tokens=12, output_tokens=3),
    )
    client = _mock_client(response)
    c = OpenAIClient(client=client)
    out = [m async for m in c.ask("hi")]
    assert isinstance(out[0], TextOutput)
    assert out[0].content == "hello"
    assert out[0].usage.input_tokens == 12
    assert out[0].usage.output_tokens == 3


@pytest.mark.asyncio
async def test_reasoning_item_parsed():
    response = _resp(
        [
            ns(
                type="reasoning",
                id="rs_1",
                summary=[ns(type="summary_text", text="thinking")],
                encrypted_content="opaque",
            ),
            ns(
                type="message",
                content=[ns(type="output_text", text="answer")],
            ),
        ],
        usage=ns(
            input_tokens=10,
            output_tokens=20,
            output_tokens_details=ns(reasoning_tokens=8),
        ),
    )
    client = _mock_client(response)
    c = OpenAIClient(client=client, reasoning="medium")
    out = [m async for m in c.ask("hi")]
    assert isinstance(out[0], Reasoning)
    assert out[0].provider_id == "rs_1"
    assert out[0].encrypted_content == "opaque"
    assert isinstance(out[1], TextOutput)
    # Usage attached to the last message in the turn
    assert out[1].usage.reasoning_tokens == 8


@pytest.mark.asyncio
async def test_function_call_executes_tool(fake_tool):
    # First response: function_call. Second: text "done".
    first = _resp(
        [
            ns(
                type="function_call",
                call_id="call_1",
                name="fake_tool",
                arguments=json.dumps({"x": "v"}),
            )
        ]
    )
    second = _resp([ns(type="message", content=[ns(type="output_text", text="done")])])
    client = AsyncMock()
    client.responses.create = AsyncMock(side_effect=[first, second])

    c = OpenAIClient(client=client, tools={"fake_tool": fake_tool})
    out = [m async for m in c.ask("go")]

    assert isinstance(out[0], ToolCall)
    assert out[0].arguments == {"x": "v"}
    assert isinstance(out[1], ToolOutput)
    assert out[1].content == "fake result"
    assert isinstance(out[2], TextOutput)
    assert out[2].content == "done"
    # Verify second call's input contains the function_call_output item
    second_kwargs = client.responses.create.call_args_list[1].kwargs
    types_in_input = [item.get("type") for item in second_kwargs["input"]]
    assert "function_call" in types_in_input
    assert "function_call_output" in types_in_input


@pytest.mark.asyncio
async def test_request_includes_tools_and_reasoning():
    response = _resp([ns(type="message", content=[ns(type="output_text", text="ok")])])
    client = _mock_client(response)
    c = OpenAIClient(
        client=client,
        system_prompt="be helpful",
        reasoning="high",
        enable_web_search=True,
    )
    [m async for m in c.ask("hi")]
    kwargs = client.responses.create.call_args.kwargs
    assert kwargs["instructions"] == "be helpful"
    assert kwargs["reasoning"] == {"effort": "high"}
    tool_types = {t["type"] for t in kwargs["tools"]}
    assert "web_search" in tool_types


@pytest.mark.asyncio
async def test_local_tool_in_request(fake_tool):
    response = _resp([ns(type="message", content=[ns(type="output_text", text="ok")])])
    client = _mock_client(response)
    c = OpenAIClient(client=client, tools={"fake_tool": fake_tool})
    [m async for m in c.ask("hi")]
    kwargs = client.responses.create.call_args.kwargs
    func_tools = [t for t in kwargs["tools"] if t["type"] == "function"]
    assert len(func_tools) == 1
    assert func_tools[0]["name"] == "fake_tool"
    # Responses API expects flat shape (no nested "function")
    assert "function" not in func_tools[0]


@pytest.mark.asyncio
async def test_user_image_input_converted():
    response = _resp([ns(type="message", content=[ns(type="output_text", text="ok")])])
    client = _mock_client(response)
    c = OpenAIClient(client=client)
    [
        m
        async for m in c.ask(
            [UserText(content="describe"), UserImage(url="http://x/y.png")]
        )
    ]
    kwargs = client.responses.create.call_args.kwargs
    # Two items: text user message, image user message
    types = [item.get("content")[0]["type"] for item in kwargs["input"]]
    assert "input_text" in types
    assert "input_image" in types


@pytest.mark.asyncio
async def test_web_search_call_yields_server_tool_messages():
    response = _resp(
        [
            ns(
                type="web_search_call",
                id="ws_1",
                action={"query": "vibecoder"},
                status="completed",
            ),
            ns(type="message", content=[ns(type="output_text", text="found")]),
        ]
    )
    client = _mock_client(response)
    c = OpenAIClient(client=client, enable_web_search=True)
    out = [m async for m in c.ask("search please")]
    assert isinstance(out[0], ServerToolUse)
    assert out[0].tool_name == "web_search"
    assert isinstance(out[1], ServerToolResult)
    assert isinstance(out[2], TextOutput)


@pytest.mark.asyncio
async def test_history_passed_to_subsequent_call():
    response = _resp([ns(type="message", content=[ns(type="output_text", text="ok")])])
    client = _mock_client(response)
    c = OpenAIClient(
        client=client,
        history=[
            UserText(content="prior"),
            TextOutput(content="prior reply"),
        ],
    )
    [m async for m in c.ask("now")]
    kwargs = client.responses.create.call_args.kwargs
    # Three items: prior user, prior assistant, current user
    assert len(kwargs["input"]) == 3
    assert kwargs["input"][0]["role"] == "user"
    assert kwargs["input"][1]["role"] == "assistant"
    assert kwargs["input"][2]["role"] == "user"
