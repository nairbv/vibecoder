import asyncio
import random
from typing import AsyncIterator

from vibecoder.agents.agent import (  # Import the AgentResponse class
    AgentResponse,
    BaseAgent,
    ToolUse,
)


class MockAgent(BaseAgent):
    def __init__(self, tools, model="default-model"):
        self.tools = tools
        self.model = model
        self.messages = []

    def set_model(self, model: str):
        """Set a new model for the mock agent."""
        self.model = model

    async def ask(self, user_input: str) -> AsyncIterator[AgentResponse]:
        self.messages.append({"role": "user", "content": user_input})

        # Simple static response or a placeholder logic
        lorem_ipsum = [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi.",
            """Duis -- a multi line message helps us make sure scroll works correctly per line
            aute irure
            dolor in reprehenderit
            in voluptate 
            velit
            esse.""",
            "Cillum dolore eu fugiat nulla pariatur.",
            "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia.",
            "Deserunt mollit anim id est laborum.",
            "Curabitur pretium tincidunt lacus.",
            "Nulla gravida orci a odio.",
            "Nullam varius, turpis et commodo pharetra, est eros bibendum elit.",
        ]

        yield AgentResponse(content=lorem_ipsum[0])  # Yield structured response

        for _ in range(7):
            await asyncio.sleep(0.01)  # Fake slight delay for pacing
            yield AgentResponse(content=random.choice(lorem_ipsum))
        yield ToolUse(tool_name="mock", arguments=["a", "b", "c"])
        yield AgentResponse(content=random.choice(lorem_ipsum))
        return
