import asyncio
from typing import AsyncIterator
import random

class MockAgent:
    def __init__(self, tools):
        self.tools = tools
        self.messages = []

    async def ask(self, user_input: str) -> AsyncIterator[str]:
        self.messages.append({"role": "user", "content": user_input})

        # Simple static response or a placeholder logic
        lorem_ipsum = [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi.",
            "Duis aute irure dolor in reprehenderit in voluptate velit esse.",
            "Cillum dolore eu fugiat nulla pariatur.",
            "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia.",
            "Deserunt mollit anim id est laborum.",
            "Curabitur pretium tincidunt lacus.",
            "Nulla gravida orci a odio.",
            "Nullam varius, turpis et commodo pharetra, est eros bibendum elit."
        ]

        yield lorem_ipsum[0]

        for _ in range(9):
            await asyncio.sleep(0.01)  # Fake slight delay, help REPL pacing
            yield random.choice(lorem_ipsum)
        return
