import pytest
from vibecoder.agents.mock_agent import MockAgent
from vibecoder.agents.agent import Agent
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_mock_agent_basic_response():
    tools = {}
    mock_agent = MockAgent(tools)

    responses = [resp async for resp in mock_agent.ask("example input")]

    assert len(responses) == 10
    assert all(isinstance(line, str) for line in responses)
    assert "Lorem ipsum" in responses[0]  # Given the response is lorem ipsum

@pytest.mark.asyncio
async def test_compare_mock_with_agent():
    tools = {}

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=AsyncMock(
        choices=[AsyncMock(
            message=AsyncMock(content="Lorem ipsum test", tool_calls=None)
        )]
    ))

    real_agent = Agent(system_prompt="test", tools=tools, client=mock_client)

    real_response = [resp async for resp in real_agent.ask("example input")]

    mock_agent = MockAgent(tools)
    mock_response = [resp async for resp in mock_agent.ask("example input")]

    assert len(real_response) == 1
    assert len(mock_response) == 10
    assert "Lorem ipsum" in mock_response[0]
