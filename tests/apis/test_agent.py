from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from vibecoder.agents.agent import AgentResponse, OpenAIAgent
from vibecoder.tools.base import Tool


@pytest_asyncio.fixture
async def mock_openai_client():
    mock_client = AsyncMock()
    mock_create = AsyncMock()
    mock_response = AsyncMock()
    mock_choice = AsyncMock()
    mock_choice.message.content = "response content"
    mock_choice.message.tool_calls = None
    mock_response.choices = [mock_choice]
    mock_create.return_value = mock_response
    mock_client.chat.completions.create = mock_create
    return mock_client


@pytest_asyncio.fixture
async def mock_tool():
    mock_tool = AsyncMock(spec=Tool)
    mock_tool.signature = "mock_tool_signature"
    mock_tool.run.return_value = "tool result"
    return mock_tool


@pytest.mark.asyncio
async def test_agent_initialization(mock_openai_client, mock_tool):
    # Use mock_openai_client and mock_tool directly without awaiting them
    agent = OpenAIAgent(
        mock_openai_client,
        system_prompt="Test prompt",
        tools={"tool_name": mock_tool},
    )
    assert agent.model == "gpt-4.1-mini"
    assert agent.tools == {"tool_name": mock_tool}
    assert agent.messages == [{"role": "system", "content": "Test prompt"}]


@pytest.mark.asyncio
async def test_agent_ask_with_response(mock_openai_client, mock_tool):
    # Use mock_openai_client and mock_tool directly without awaiting them
    agent = OpenAIAgent(
        mock_openai_client,
        system_prompt="Test prompt",
        tools={"tool_name": mock_tool},
    )
    generator = agent.ask("user question")
    response_content = await generator.__anext__()
    assert response_content == AgentResponse(message="response content")
    mock_openai_client.chat.completions.create.assert_called_once()
