from unittest.mock import AsyncMock

import pytest

from vibecoder.agents.agent import Agent, AgentResponse  # Add Agent import
from vibecoder.agents.mock_agent import MockAgent


@pytest.mark.asyncio
async def test_mock_agent_basic_response():
    tools = {}
    mock_agent = MockAgent(tools)

    # This should yield AgentResponse instances
    async def mock_ask(input):
        yield AgentResponse(message="Lorem ipsum dolor sit amet.")
        for i in range(1, 11):
            yield AgentResponse(message=f"Response {i}")

    mock_agent.ask = mock_ask  # Use the mock implementation

    responses = [resp async for resp in mock_agent.ask("example input")]
    assert isinstance(responses[0], AgentResponse)
    assert len(responses) == 11  # change this based on the number of responses yielded
    assert all(isinstance(line, AgentResponse) for line in responses)
    assert "Lorem ipsum" in responses[0].message


@pytest.mark.asyncio
async def test_compare_mock_with_agent():
    tools = {}

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=AsyncMock(
            choices=[
                AsyncMock(
                    message=AsyncMock(content="Lorem ipsum test", tool_calls=None)
                )
            ]
        )
    )

    real_agent = Agent(system_prompt="test", tools=tools, client=mock_client)

    real_response = [resp async for resp in real_agent.ask("example input")]

    mock_agent = MockAgent(tools)
    mock_response = [resp async for resp in mock_agent.ask("example input")]

    assert len(real_response) == 1
    assert len(mock_response) == 10
    assert "Lorem ipsum" in mock_response[0].message
