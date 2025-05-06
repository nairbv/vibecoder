import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, AsyncIterator, Dict, Iterator

from vibecoder.tools.base import Tool


@dataclass
class AgentMessage(ABC):
    """Base class for all agent messages."""

    input_tokens: int = 0
    output_tokens: int = 0
    content: str = ""

    @abstractmethod
    def to_openai_dict(self) -> dict:
        pass

    def to_anthropic_dict(self) -> dict:
        return self.to_openai_dict()


@dataclass
class UserMessage(AgentMessage):
    def to_openai_dict(self):
        return {"role": "user", "content": self.content}


@dataclass
class AgentResponse(AgentMessage):
    def to_openai_dict(self):
        return {"role": "assistant", "content": self.content}


@dataclass
class ToolUse(AgentMessage):
    tool_name: str = ""
    tool_call_id: str = ""
    arguments: dict[str] = field(default_factory=list)

    def to_openai_dict(self):
        return {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": self.tool_call_id,
                    "function": {
                        "arguments": json.dumps(self.arguments),
                        "name": self.tool_name,
                    },
                    "type": "function",
                }
            ],
        }

    def to_anthropic_dict(self):
        return {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": self.tool_call_id,
                    "name": self.tool_name,
                    "input": self.arguments,
                }
            ],
        }


@dataclass
class ToolResult(AgentMessage):
    tool_name: str = ""
    tool_call_id: str = ""
    arguments: dict[str] = field(default_factory=list)

    def to_openai_dict(self):
        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "content": self.content,
        }

    def to_anthropic_dict(self):
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": self.tool_call_id,
                    "content": self.content,
                }
            ],
        }


class BaseAgent(ABC):
    @abstractmethod
    def set_model(self, model: str) -> None:
        pass

    @abstractmethod
    async def ask(self, user_input: str) -> AsyncIterator[AgentMessage]:
        pass


class OpenAIAgent(BaseAgent):
    def __init__(
        self,
        client,
        system_prompt: str = "",
        tools: Dict[str, Tool] = {},
        model: str = "gpt-4.1-mini",
        messages: list[AgentMessage] = [],
    ):
        self.model = model
        self.tools = tools
        self.client = client
        self.messages = [{"role": "system", "content": system_prompt}]
        for message in messages:
            self.messages.append(message.to_openai_dict())

    def set_model(self, model: str):
        """Set a new model for the agent to use."""
        self.model = model

    async def ask(self, user_input: str) -> AsyncIterator[AgentMessage]:
        self.messages.append({"role": "user", "content": user_input})

        while True:

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=False,
                tools=[tool.signature for tool in self.tools.values()],
            )

            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens

            choice = response.choices[0]
            if hasattr(choice.message, "content") and choice.message.content:
                response = AgentResponse(
                    content=choice.message.content,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                yield response
                self.messages.append(response.to_openai_dict())

            if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                for call in choice.message.tool_calls:

                    tool_name = call.function.name
                    args = json.loads(call.function.arguments)

                    tool_use = ToolUse(
                        tool_name=tool_name,
                        tool_call_id=call.id,
                        arguments=args,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )
                    yield tool_use

                    if tool_name not in self.tools:
                        result = f"[Tool {tool_name} not implemented]"
                    else:
                        result = self.tools[tool_name].run(args)
                        if len(result):
                            result += "\n"

                    tool_result = ToolResult(
                        content=result,
                        tool_name=tool_name,
                        tool_call_id=call.id,
                        arguments=args,
                    )
                    yield tool_result

                    self.messages.append(tool_use.to_openai_dict())
                    self.messages.append(tool_result.to_openai_dict())
            else:
                break
        return


class AnthropicAgent(BaseAgent):
    def __init__(
        self,
        client,
        system_prompt: str = "",
        tools: Dict[str, Tool] = {},
        model: str = "claude-3-5-haiku-latest",
        messages: list[dict] = [],
    ):
        self.model = model
        self.tools = tools
        self.client = client
        self.messages = [message.to_anthropic_dict() for message in messages]
        self.system_prompt = system_prompt

    def set_model(self, model: str):
        """Set a new model for the agent to use."""
        self.model = model

    def _convert_tools(self):
        """Convert tools to Anthropic's expected format."""
        converted_tools = []
        for tool in self.tools.values():
            sig = tool.signature["function"]
            params = (sig.get("parameters", {}),)
            anth_tool = {
                "name": sig["name"],
                "description": sig.get("description", ""),
                "input_schema": {"type": "object", "properties": {}, "required": []},
            }
            if "properties" in params:
                anth_tool["input_schema"]["properties"] = sig["properties"]
            if "required" in params:
                anth_tool["input_schema"]["required"] = sig["required"]

            converted_tools.append(anth_tool)
        return converted_tools

    async def ask(self, user_input: str) -> AsyncIterator[AgentMessage]:
        self.messages.append({"role": "user", "content": user_input})

        while True:
            response = await self.client.messages.create(
                model=self.model,
                messages=self.messages,
                tools=self._convert_tools(),
                stream=False,
                max_tokens=4096,
                system=self.system_prompt,
            )

            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens

            has_tool_use = False
            for content_block in response.content:
                if content_block.type == "text":
                    response = AgentResponse(
                        content_block.text,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )
                    yield response
                    self.messages.append(response.to_anthropic_dict())

                elif content_block.type == "tool_use":
                    has_tool_use = True
                    tool_use = content_block
                    tool_name = tool_use.name
                    args = tool_use.input

                    tool_use = ToolUse(
                        tool_name=tool_name,
                        tool_call_id=tool_use.id,
                        arguments=args,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )
                    yield tool_use

                    if tool_name not in self.tools:
                        result = f"[Tool {tool_name} not implemented]"
                    else:
                        result = self.tools[tool_name].run(args)
                        if len(result):
                            result += "\n"

                    tool_result = ToolResult(
                        tool_name=tool_name,
                        tool_call_id=tool_use.id,
                        arguments=args,
                        content=result,
                    )

                    yield tool_result

                    self.messages.append(tool_use.to_anthropic_dict())
                    self.messages.append(tool_result.to_anthropic_dict())

            if has_tool_use:
                continue
            else:
                break
        return
