import json
import os

from dotenv import load_dotenv
from typing import AsyncGenerator, AsyncIterator, Dict, Iterator
from openai import OpenAI, AsyncOpenAI
from vibecoder.tools.base import Tool

load_dotenv()

class Agent:
    def __init__(self, system_prompt: str, tools: Dict[str, Tool], model: str = "gpt-4o", client=None):
        self.model = model
        self.tools = tools
        self.client = client or AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=0)
        self.messages = [
            {"role": "system", "content": system_prompt}
        ]

    def set_model(self, model: str):
        """Set a new model for the agent to use."""
        self.model = model

    async def ask(self, user_input: str) -> AsyncIterator[str]:
        self.messages.append({"role": "user", "content": user_input})

        while True:

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=False,
                tools=[tool.signature for tool in self.tools.values()],
            )

            choice = response.choices[0]
            if hasattr(choice.message, "content") and choice.message.content:
                self.messages.append({"role": "assistant", "content": choice.message.content})
                yield choice.message.content

            if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                for call in choice.message.tool_calls:
                    tool_name = call.function.name
                    args = json.loads(call.function.arguments)

                    args_str = str(args)
                    if len(args_str) > 200:
                        args_str = args_str[:200] + "..."
                    yield f"{tool_name}({args_str})\n"

                    if tool_name not in self.tools:
                        result = f"[Tool {tool_name} not implemented]"
                    else:
                        result = self.tools[tool_name].run(args)
                        if len(result):
                            result += "\n"

                    # yield result

                    self.messages.append({
                        "role": "assistant",
                        "tool_calls": [call.model_dump()]
                    })

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result
                    })
            else:
                break
        return
