"""Tests for BaseClient ask-loop semantics, using MockClient."""

from __future__ import annotations

import pytest

from vibecoder.clients import (
    MockClient,
    Reasoning,
    TextOutput,
    ToolCall,
    ToolOutput,
    Usage,
    UserImage,
    UserText,
    create_client,
)


@pytest.mark.asyncio
async def test_simple_text_turn():
    c = MockClient(scripts=[[TextOutput(content="hello")]])
    out = [m async for m in c.ask("hi")]
    assert isinstance(out[0], TextOutput)
    assert out[0].content == "hello"
    # History contains: UserText("hi"), TextOutput("hello")
    assert isinstance(c.history[0], UserText)
    assert c.history[0].content == "hi"
    assert isinstance(c.history[1], TextOutput)


@pytest.mark.asyncio
async def test_string_input_normalizes_to_user_text():
    c = MockClient(scripts=[[TextOutput(content="ok")]])
    [m async for m in c.ask("question")]
    assert c.history[0] == UserText(content="question")


@pytest.mark.asyncio
async def test_message_input_passes_through():
    c = MockClient(scripts=[[TextOutput(content="ok")]])
    img = UserImage(url="https://example.com/x.png")
    [m async for m in c.ask([UserText(content="describe"), img])]
    assert c.history[0].content == "describe"
    assert c.history[1] is img


@pytest.mark.asyncio
async def test_tool_call_executes_local_tool(fake_tool):
    c = MockClient(
        tools={"fake_tool": fake_tool},
        scripts=[
            [ToolCall(tool_name="fake_tool", tool_call_id="t1", arguments={"x": "v"})],
            [TextOutput(content="done")],
        ],
    )
    out = [m async for m in c.ask("go")]
    # Sequence: ToolCall, ToolOutput, TextOutput
    assert isinstance(out[0], ToolCall)
    assert isinstance(out[1], ToolOutput)
    assert out[1].content == "fake result"
    assert isinstance(out[2], TextOutput)
    # Tool was actually invoked with our arguments
    assert fake_tool.last_call.arguments == {"x": "v"}


@pytest.mark.asyncio
async def test_tool_call_unknown_tool_returns_error():
    c = MockClient(
        scripts=[
            [ToolCall(tool_name="missing", tool_call_id="t1", arguments={})],
            [TextOutput(content="ok")],
        ],
    )
    out = [m async for m in c.ask("go")]
    assert isinstance(out[1], ToolOutput)
    assert out[1].is_error is True
    assert "not implemented" in out[1].content


@pytest.mark.asyncio
async def test_loop_terminates_when_no_tool_call():
    c = MockClient(
        scripts=[
            [TextOutput(content="just text")],
            [TextOutput(content="should not be reached")],
        ],
    )
    out = [m async for m in c.ask("go")]
    assert len(out) == 1
    # Second script untouched
    assert c._turn_index == 1


@pytest.mark.asyncio
async def test_history_grows_across_calls():
    c = MockClient(
        scripts=[[TextOutput(content="r1")], [TextOutput(content="r2")]],
    )
    [m async for m in c.ask("q1")]
    [m async for m in c.ask("q2")]
    # 4 entries: q1, r1, q2, r2
    assert len(c.history) == 4


@pytest.mark.asyncio
async def test_set_model():
    c = MockClient(scripts=[])
    c.set_model("model-x")
    assert c.model == "model-x"


@pytest.mark.asyncio
async def test_factory_mock():
    c = create_client("mock", scripts=[[TextOutput(content="hi")]])
    assert isinstance(c, MockClient)
    out = [m async for m in c.ask("yo")]
    assert out[0].content == "hi"


@pytest.mark.asyncio
async def test_factory_unknown_provider_raises():
    with pytest.raises(ValueError):
        create_client("nope")


@pytest.mark.asyncio
async def test_yielded_messages_appended_in_order():
    c = MockClient(
        scripts=[
            [
                Reasoning(content="thinking..."),
                TextOutput(
                    content="answer", usage=Usage(input_tokens=10, output_tokens=5)
                ),
            ]
        ],
    )
    out = [m async for m in c.ask("q")]
    assert isinstance(out[0], Reasoning)
    assert isinstance(out[1], TextOutput)
    # Final message carries usage
    assert out[1].usage.input_tokens == 10
