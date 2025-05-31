import base64
import hashlib
import json
import re
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict

from vibecoder.messages import AgentMessage, AgentResponse, ToolResult, ToolUse
from vibecoder.tools.base import Tool


def to_openai_tool_call_id(original: str) -> str:
    if len(original) < 40:
        return original
    # Hash and base64-encode
    h = hashlib.sha256(original.encode()).digest()
    b64 = base64.b64encode(h).decode()

    # Remove non-alphanumerics (Base64 includes + and /)
    alnum = re.sub(r"[^a-zA-Z0-9]", "", b64)

    # Truncate to fit within 40 chars total, accounting for "call_"
    return "call_" + alnum[:35]


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
            # ensure compliance with openai's 40-char tool call id limit.
            if isinstance(message, ToolUse) or isinstance(message, ToolResult):
                message.tool_call_id = to_openai_tool_call_id(message.tool_call_id)

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

                    # Execute tool and wrap result in ToolResult
                    if tool_name not in self.tools:
                        content = f"[Tool {tool_name} not implemented] Available tools: {', '.join(self.tools.keys())}"
                        tool_result = ToolResult(
                            content=content,
                            tool_name=tool_name,
                            tool_call_id=call.id,
                        )
                    else:
                        # Delegate execution to tool.run, which returns a ToolResult
                        tool_result = await self.tools[tool_name].run(tool_use)
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
            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens

            has_tool_use = False
            for content_block in response.content:
                if content_block.type == "text":
                    response = AgentResponse(
                        content=content_block.text,
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

                    tool_use_msg = ToolUse(
                        tool_name=tool_name,
                        tool_call_id=tool_use.id,
                        arguments=args,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )
                    yield tool_use_msg

                    # Execute tool and wrap result
                    if tool_name not in self.tools:
                        content = f"[Tool {tool_name} not implemented]"
                        tool_result = ToolResult(
                            content=content,
                            tool_name=tool_name,
                            tool_call_id=tool_use.id,
                        )
                    else:
                        tool_result = await self.tools[tool_name].run(tool_use_msg)

                    yield tool_result

                    # Append tool use and result to messages
                    self.messages.append(tool_use_msg.to_anthropic_dict())
                    self.messages.append(tool_result.to_anthropic_dict())

            if has_tool_use:
                continue
            else:
                break
        return
