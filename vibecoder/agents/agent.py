import json
from abc import ABC
from dataclasses import dataclass
from typing import AsyncGenerator, AsyncIterator, Dict, Iterator

from vibecoder.tools.base import Tool


class AgentOutput(ABC):
    """Base class for all agent messages."""


@dataclass
class AgentResponse(AgentOutput):
    message: str


@dataclass
class ToolUse(AgentOutput):
    name: str
    arguments: list[str]


class OpenAIAgent:
    def __init__(
        self,
        client,
        system_prompt: str = "",
        tools: Dict[str, Tool] = {},
        model: str = "gpt-4.1-mini",
    ):
        self.model = model
        self.tools = tools
        self.client = client
        self.messages = [{"role": "system", "content": system_prompt}]

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
                self.messages.append(
                    {"role": "assistant", "content": choice.message.content}
                )
                yield AgentResponse(choice.message.content)

            if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                for call in choice.message.tool_calls:
                    tool_name = call.function.name
                    args = json.loads(call.function.arguments)

                    yield ToolUse(
                        name=tool_name, arguments=args
                    )  # f"{tool_name}({args_str})\n"

                    if tool_name not in self.tools:
                        result = f"[Tool {tool_name} not implemented]"
                    else:
                        result = self.tools[tool_name].run(args)
                        if len(result):
                            result += "\n"

                    # yield result

                    self.messages.append(
                        {"role": "assistant", "tool_calls": [call.model_dump()]}
                    )

                    self.messages.append(
                        {"role": "tool", "tool_call_id": call.id, "content": result}
                    )
            else:
                break
        return


class AnthropicAgent:
    def __init__(
        self,
        client,
        system_prompt: str = "",
        tools: Dict[str, Tool] = {},
        model: str = "claude-3-sonnet-20240229",
    ):
        self.model = model
        self.tools = tools
        self.client = client
        self.messages = (
            [{"role": "user", "content": system_prompt}] if system_prompt else []
        )

    def set_model(self, model: str):
        """Set a new model for the agent to use."""
        self.model = model

    def _convert_tools(self):
        """Convert tools to Anthropic's expected format."""
        converted_tools = []
        for tool in self.tools.values():
            sig = tool.signature["function"]
            converted_tools.append(
                {
                    "name": sig["name"],
                    "description": sig.get("description", ""),
                    "input_schema": sig.get("parameters", {}),
                    "type": "function",
                }
            )
        return converted_tools

    async def ask(self, user_input: str) -> AsyncIterator[AgentOutput]:
        self.messages.append({"role": "user", "content": user_input})

        while True:
            response = await self.client.messages.create(
                model=self.model,
                messages=self.messages,
                tools=self._convert_tools(),
                stream=False,
            )

            for content_block in response.content:
                if content_block.type == "text":
                    self.messages.append(
                        {"role": "assistant", "content": content_block.text}
                    )
                    yield AgentResponse(content_block.text)

                elif content_block.type == "tool_use":
                    tool_name = content_block.name
                    args = content_block.input

                    yield ToolUse(name=tool_name, arguments=args)

                    if tool_name not in self.tools:
                        result = f"[Tool {tool_name} not implemented]"
                    else:
                        result = self.tools[tool_name].run(args)
                        if len(result):
                            result += "\n"

                    self.messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": content_block.id,
                                    "content": result,
                                }
                            ],
                        }
                    )
                    break  # After tool use, send result and get next response
            else:
                break
