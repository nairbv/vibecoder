import asyncio

import pytest

from vibecoder.agent_status import RespondingStatus, WaitingStatus, WorkingStatus
from vibecoder.agents.agent import BaseAgent
from vibecoder.agents.mock_agent import MockAgent
from vibecoder.messages import AgentResponse, ToolResult, ToolUse
from vibecoder.session import Session


class OutputCollector:
    """Test helper that captures Session callbacks."""

    def __init__(self):
        self.lines: list[tuple[str, str]] = []
        self.statuses: list = []
        self.exit_called: bool = False

    def on_output(self, text: str, style: str = "application"):
        self.lines.append((text, style))

    def on_status(self, status):
        self.statuses.append(status)

    def on_exit(self):
        self.exit_called = True

    @property
    def texts(self) -> list[str]:
        return [text for text, _ in self.lines]

    @property
    def last_text(self) -> str:
        return self.lines[-1][0] if self.lines else ""


class SimpleAgent(BaseAgent):
    """A minimal agent for testing that yields a single canned response."""

    def __init__(self, responses=None):
        self.model = "test-model"
        self.messages = []
        self._responses = responses or [AgentResponse(content="test reply")]

    def set_model(self, model: str):
        self.model = model

    async def ask(self, user_input: str):
        self.messages.append(user_input)
        for r in self._responses:
            yield r


def make_session(collector: OutputCollector, agent=None, factory=None) -> Session:
    """Create a Session wired to an OutputCollector."""
    if factory is None:
        default_agent = agent or SimpleAgent()
        factory = lambda role: default_agent
    return Session(
        on_output=collector.on_output,
        on_status=collector.on_status,
        on_exit=collector.on_exit,
        agent_factory=factory,
        default_role="swe",
    )


# --- Command dispatch tests ---


@pytest.mark.asyncio
async def test_quit_calls_on_exit():
    c = OutputCollector()
    s = make_session(c)
    await s.handle_command("quit")
    assert c.exit_called
    assert "Exiting" in c.last_text


@pytest.mark.asyncio
async def test_exit_calls_on_exit():
    c = OutputCollector()
    s = make_session(c)
    await s.handle_command("exit")
    assert c.exit_called


@pytest.mark.asyncio
async def test_unknown_command():
    c = OutputCollector()
    s = make_session(c)
    await s.handle_command("foobar")
    assert "Unknown command" in c.last_text
    assert "/foobar" in c.last_text


@pytest.mark.asyncio
async def test_model_query():
    c = OutputCollector()
    s = make_session(c)
    await s.handle_command("model")
    assert "test-model" in c.last_text


@pytest.mark.asyncio
async def test_model_set():
    c = OutputCollector()
    s = make_session(c)
    await s.handle_command("model gpt-4o")
    assert s.agent.model == "gpt-4o"
    assert "gpt-4o" in c.last_text


@pytest.mark.asyncio
async def test_interrupt_command():
    c = OutputCollector()
    s = make_session(c)
    await s.handle_command("interrupt")
    assert s._interrupted
    assert "Interrupt" in c.last_text


# --- Role switching tests ---


@pytest.mark.asyncio
async def test_switch_role_same_role():
    c = OutputCollector()
    s = make_session(c)
    await s.switch_role("swe")
    assert "Already using" in c.last_text


@pytest.mark.asyncio
async def test_switch_role_unknown():
    c = OutputCollector()
    s = make_session(c)
    await s.switch_role("nonexistent")
    assert "Unknown agent role" in c.last_text


@pytest.mark.asyncio
async def test_switch_role_creates_agent_lazily():
    agents_created = []

    def tracking_factory(role):
        agent = SimpleAgent()
        agents_created.append(role)
        return agent

    c = OutputCollector()
    s = make_session(c, factory=tracking_factory)
    # Factory called once for default "swe"
    assert agents_created == ["swe"]

    await s.switch_role("mock")
    assert "mock" in agents_created
    assert s.agent_type == "mock"
    assert "Switched to mock" in c.last_text


@pytest.mark.asyncio
async def test_switch_role_reuses_existing():
    agents_created = []

    def tracking_factory(role):
        agent = SimpleAgent()
        agents_created.append(role)
        return agent

    c = OutputCollector()
    s = make_session(c, factory=tracking_factory)

    await s.switch_role("mock")
    first_mock = s.agent
    await s.switch_role("swe")
    await s.switch_role("mock")
    # mock should only have been created once (not again on second switch)
    assert agents_created.count("mock") == 1
    assert s.agent is first_mock


# --- Ask loop tests ---


@pytest.mark.asyncio
async def test_ask_agent_response():
    c = OutputCollector()
    agent = SimpleAgent([AgentResponse(content="hello world")])
    s = make_session(c, agent=agent)

    await s.ask("hi")
    assert any("hello world" in t for t in c.texts)
    assert any("hello world" in o for o in s.last_output)


@pytest.mark.asyncio
async def test_ask_tool_use():
    c = OutputCollector()
    agent = SimpleAgent(
        [
            ToolUse(tool_name="grep", tool_call_id="123", arguments={"pattern": "foo"}),
        ]
    )
    s = make_session(c, agent=agent)

    await s.ask("search for foo")
    assert any("Tool call" in t and "grep" in t for t in c.texts)


@pytest.mark.asyncio
async def test_ask_tool_result():
    c = OutputCollector()
    agent = SimpleAgent(
        [
            ToolResult(content="found 3 matches", tool_name="grep", tool_call_id="123"),
        ]
    )
    s = make_session(c, agent=agent)

    await s.ask("search")
    assert any("ToolResult(grep)" in t for t in c.texts)


@pytest.mark.asyncio
async def test_ask_with_mock_agent():
    """Test with the real MockAgent to ensure compatibility."""
    c = OutputCollector()
    mock = MockAgent(tools={})
    s = make_session(c, agent=mock)

    await s.ask("tell me something")
    # MockAgent yields multiple AgentResponse + a ToolUse
    agent_responses = [t for t in c.texts if "SWE:" in t]
    tool_calls = [t for t in c.texts if "Tool call" in t]
    assert len(agent_responses) >= 1
    assert len(tool_calls) >= 1
    assert len(s.last_output) >= 1


@pytest.mark.asyncio
async def test_ask_long_tool_args_truncated():
    c = OutputCollector()
    long_args = {"data": "x" * 300}
    agent = SimpleAgent(
        [
            ToolUse(tool_name="write_file", tool_call_id="456", arguments=long_args),
        ]
    )
    s = make_session(c, agent=agent)

    await s.ask("write something big")
    tool_lines = [t for t in c.texts if "Tool call" in t]
    assert len(tool_lines) == 1
    assert "..." in tool_lines[0]


@pytest.mark.asyncio
async def test_ask_long_tool_result_truncated():
    c = OutputCollector()
    agent = SimpleAgent(
        [
            ToolResult(content="a" * 200, tool_name="read_file", tool_call_id="789"),
        ]
    )
    s = make_session(c, agent=agent)

    await s.ask("read")
    result_lines = [t for t in c.texts if "ToolResult" in t]
    assert len(result_lines) == 1
    assert "..." in result_lines[0]


# --- handle_line routing tests ---


@pytest.mark.asyncio
async def test_handle_line_routes_command():
    c = OutputCollector()
    s = make_session(c)
    await s.handle_line("/model")
    assert "test-model" in c.last_text


@pytest.mark.asyncio
async def test_handle_line_routes_ask():
    c = OutputCollector()
    agent = SimpleAgent([AgentResponse(content="got it")])
    s = make_session(c, agent=agent)
    await s.handle_line("do something")
    assert any("got it" in t for t in c.texts)


@pytest.mark.asyncio
async def test_handle_line_updates_status():
    c = OutputCollector()
    agent = SimpleAgent([AgentResponse(content="ok")])
    s = make_session(c, agent=agent)
    await s.handle_line("hello")
    # Should have set RespondingStatus then WaitingStatus
    assert len(c.statuses) >= 2
    assert isinstance(c.statuses[0], RespondingStatus)
    assert isinstance(c.statuses[-1], WaitingStatus)


# --- Work mode tests ---


@pytest.mark.asyncio
async def test_work_mode_interrupt():
    c = OutputCollector()
    call_count = 0

    class InterruptAfterOneAgent(BaseAgent):
        def __init__(self):
            self.model = "test"

        def set_model(self, model):
            self.model = model

        async def ask(self, user_input):
            nonlocal call_count
            call_count += 1
            yield AgentResponse(content=f"working {call_count}")

    agent = InterruptAfterOneAgent()
    s = make_session(c, agent=agent)

    # Interrupt after the first ask completes
    async def interrupt_soon():
        await asyncio.sleep(0.05)
        s._interrupted = True

    asyncio.create_task(interrupt_soon())
    await s.start_working("work 1")

    assert "Entering autonomous work mode" in c.texts[0]
    assert "Finished autonomous work mode" in c.last_text
    assert any(isinstance(st, WorkingStatus) for st in c.statuses)
    assert any(isinstance(st, WaitingStatus) for st in c.statuses)


# --- Error handling tests ---


@pytest.mark.asyncio
async def test_ask_handles_agent_exception():
    c = OutputCollector()

    class FailingAgent(BaseAgent):
        def __init__(self):
            self.model = "fail"

        def set_model(self, model):
            self.model = model

        async def ask(self, user_input):
            raise RuntimeError("boom")
            yield  # make it a generator

    s = make_session(c, agent=FailingAgent())
    await s.ask("trigger error")
    assert any("Exception during ask" in t for t in c.texts)
    assert any("boom" in t for t in c.texts)


@pytest.mark.asyncio
async def test_handle_line_catches_exceptions():
    c = OutputCollector()

    class FailingAgent(BaseAgent):
        def __init__(self):
            self.model = "fail"

        def set_model(self, model):
            self.model = model

        async def ask(self, user_input):
            raise RuntimeError("kaboom")
            yield

    s = make_session(c, agent=FailingAgent())
    await s.handle_line("trigger")
    # handle_line wraps ask, so error should be caught
    assert any("Exception" in t for t in c.texts)
