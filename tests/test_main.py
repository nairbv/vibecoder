import os
from unittest.mock import AsyncMock, patch

import pytest

from vibecoder.agents.agent import AgentResponse, ToolUse
from vibecoder.messages import AgentResponse as MsgAgentResponse
from vibecoder.session import Session


class OutputCollector:
    def __init__(self):
        self.lines = []
        self.statuses = []
        self.exit_called = False

    def on_output(self, text, style="application"):
        self.lines.append((text, style))

    def on_status(self, status):
        self.statuses.append(status)

    def on_exit(self):
        self.exit_called = True

    @property
    def texts(self):
        return [text for text, _ in self.lines]


@pytest.fixture
def mock_agent():
    """Creates a mock agent that yields a fixed response."""

    class FixedAgent:
        def __init__(self):
            self.model = "test-model"

        def set_model(self, model):
            self.model = model

        async def ask(self, user_input):
            yield AgentResponse(content="This is a test response")

    return FixedAgent()


@pytest.mark.asyncio
async def test_context_save(mock_agent, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Create the prompt file the save_context method reads
    prompts_dir = tmp_path / "vibecoder" / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "save_context.md").write_text("Summarize the session.")

    c = OutputCollector()
    session = Session(
        on_output=c.on_output,
        on_status=c.on_status,
        on_exit=c.on_exit,
        agent_factory=lambda role: mock_agent,
    )

    await session.save_context("Test saving context")

    session_file = tmp_path / ".vibecoder" / "swe_session.md"
    assert session_file.exists()
    content = session_file.read_text()
    assert "This is a test response" in content
    assert "Context successfully saved" in c.texts[-1]


@pytest.mark.asyncio
async def test_ask_functionality(mock_agent):
    c = OutputCollector()
    session = Session(
        on_output=c.on_output,
        on_status=c.on_status,
        on_exit=c.on_exit,
        agent_factory=lambda role: mock_agent,
    )

    await session.ask("Test input for asking functionality")

    assert any("This is a test response" in t for t in c.texts)
    assert any("This is a test response" in o for o in session.last_output)
