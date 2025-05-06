from vibecoder.agents.agent import (
    AgentMessage,
    AgentResponse,
    AnthropicAgent,
    BaseAgent,
    OpenAIAgent,
    ToolResult,
    ToolUse,
    UserMessage,
)
from vibecoder.agents.mock_agent import MockAgent
from vibecoder.agents.swe import (
    build_anthropic_swe_agent,
    build_swe_agent,
    code_reviewer_analyst,
)


def create_agent_by_role(role: str):
    if role == "swe":
        return build_swe_agent()
    elif role == "mock":
        return MockAgent(tools=None)
    elif role == "anthropic":
        return build_anthropic_swe_agent()
    elif role == "analyst":
        return code_reviewer_analyst()
