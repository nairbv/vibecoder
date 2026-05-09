"""Tests for GeminiClient against a mocked google-genai async client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vibecoder.clients import (
    GeminiClient,
    Reasoning,
    TextOutput,
    ToolCall,
    ToolOutput,
    UserImage,
    UserText,
)

from .conftest import ns


def _mock_client(response):
    """Mock with `client.aio.models.generate_content`."""
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=response)
    return client


def _resp(parts, usage=None):
    return ns(
        candidates=[ns(content=ns(parts=parts))],
        usage_metadata=usage,
    )


@pytest.mark.asyncio
async def test_text_response_parsed():
    response = _resp(
        [ns(text="hello", thought=False, function_call=None)],
        usage=ns(prompt_token_count=10, candidates_token_count=5),
    )
    client = _mock_client(response)
    c = GeminiClient(client=client)
    out = [m async for m in c.ask("hi")]
    assert isinstance(out[0], TextOutput)
    assert out[0].content == "hello"
    assert out[0].usage.input_tokens == 10


@pytest.mark.asyncio
async def test_thought_part_yields_reasoning():
    response = _resp(
        [
            ns(text="thinking...", thought=True, function_call=None),
            ns(text="answer", thought=False, function_call=None),
        ],
        usage=ns(
            prompt_token_count=10,
            candidates_token_count=4,
            thoughts_token_count=12,
        ),
    )
    client = _mock_client(response)
    c = GeminiClient(client=client, reasoning="medium")
    out = [m async for m in c.ask("hi")]
    assert isinstance(out[0], Reasoning)
    assert isinstance(out[1], TextOutput)
    assert out[1].usage.reasoning_tokens == 12


@pytest.mark.asyncio
async def test_thinking_config_in_request():
    response = _resp([ns(text="ok", thought=False, function_call=None)])
    client = _mock_client(response)
    c = GeminiClient(client=client, reasoning="high")
    [m async for m in c.ask("hi")]
    kwargs = client.aio.models.generate_content.call_args.kwargs
    assert kwargs["config"]["thinking_config"]["include_thoughts"] is True


@pytest.mark.asyncio
async def test_function_call_executes_tool(fake_tool):
    first = _resp(
        [
            ns(
                text=None,
                thought=False,
                function_call=ns(name="fake_tool", args={"x": "v"}),
            )
        ]
    )
    second = _resp([ns(text="done", thought=False, function_call=None)])
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(side_effect=[first, second])
    c = GeminiClient(client=client, tools={"fake_tool": fake_tool})
    out = [m async for m in c.ask("go")]
    assert isinstance(out[0], ToolCall)
    assert out[0].arguments == {"x": "v"}
    assert isinstance(out[1], ToolOutput)
    assert isinstance(out[2], TextOutput)
    second_kwargs = client.aio.models.generate_content.call_args_list[1].kwargs
    # Tool response goes back as a function_response part
    parts_seen = []
    for content in second_kwargs["contents"]:
        for p in content["parts"]:
            parts_seen.extend(p.keys())
    assert "function_call" in parts_seen
    assert "function_response" in parts_seen


@pytest.mark.asyncio
async def test_tools_passed_with_function_declarations(fake_tool):
    response = _resp([ns(text="ok", thought=False, function_call=None)])
    client = _mock_client(response)
    c = GeminiClient(
        client=client, tools={"fake_tool": fake_tool}, enable_web_search=True
    )
    [m async for m in c.ask("hi")]
    kwargs = client.aio.models.generate_content.call_args.kwargs
    tools = kwargs["config"]["tools"]
    has_func_decl = any("function_declarations" in t for t in tools)
    has_search = any("google_search" in t for t in tools)
    assert has_func_decl
    assert has_search


@pytest.mark.asyncio
async def test_user_image_inline_data():
    response = _resp([ns(text="ok", thought=False, function_call=None)])
    client = _mock_client(response)
    c = GeminiClient(client=client)
    [
        m
        async for m in c.ask(
            [
                UserText(content="describe"),
                UserImage(data=b"\x89PNG", media_type="image/png"),
            ]
        )
    ]
    kwargs = client.aio.models.generate_content.call_args.kwargs
    user_content = kwargs["contents"][0]
    assert user_content["role"] == "user"
    keys = [list(p.keys())[0] for p in user_content["parts"]]
    assert "text" in keys
    assert "inline_data" in keys


@pytest.mark.asyncio
async def test_system_prompt_passed():
    response = _resp([ns(text="ok", thought=False, function_call=None)])
    client = _mock_client(response)
    c = GeminiClient(client=client, system_prompt="you are helpful")
    [m async for m in c.ask("hi")]
    kwargs = client.aio.models.generate_content.call_args.kwargs
    assert kwargs["config"]["system_instruction"] == "you are helpful"
