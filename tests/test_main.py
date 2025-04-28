import pytest
from vibecoder.main import REPLContextManager
from unittest.mock import AsyncMock, patch
import os
from vibecoder.agents.agent import AgentResponse, ToolUse

@pytest.fixture
def setup_mock_agent():
    """Sets up a mock agent with expected behaviors for use in tests."""
    async def mock_ask(*args, **kwargs):
        yield AgentResponse(message='This is a test response')
        yield ToolUse(name='mock_tool', arguments=['arg1', 'arg2'])  # Sample tool call
    mock_agent = AsyncMock()
    mock_agent.ask = mock_ask
    return mock_agent

@pytest.mark.asyncio
async def test_context_save(setup_mock_agent):
    with patch('vibecoder.main.build_swe_agent', return_value=setup_mock_agent):
        manager = REPLContextManager()

        user_instruction = 'Test saving context'
        await manager.save_context(user_instruction)

        with open('.vibecoder/swe_session.md', 'r') as file:
            content = file.read()
            assert 'This is a test response' in content
            assert user_instruction in content  # Should include the instruction

@pytest.mark.asyncio
async def test_ask_functionality(setup_mock_agent):
    with patch('vibecoder.main.build_swe_agent', return_value=setup_mock_agent):
        manager = REPLContextManager()

        test_line = 'Test input for asking functionality'
        await manager.ask(test_line)

        # Check that the last_output was saved correctly
        assert any(resp.message == 'This is a test response' for resp in manager.last_output if isinstance(resp, AgentResponse))
        assert any(isinstance(resp, ToolUse) for resp in manager.last_output)  # Check for ToolUse instances