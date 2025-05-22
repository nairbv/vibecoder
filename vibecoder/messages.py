import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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

    def __repr__(self):
        args_str = str(self.arguments)
        if len(args_str) > 200:
            args_str = args_str[:200] + "..."
        tool_call_str = f"{self.tool_name}({args_str})"
        text = f"🔧{tool_call_str}"
        return text

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

    def __repr__(self):
        cleaned = self.content.strip().replace("\n", "\\n")
        text = cleaned[:100]
        if len(cleaned) >= 100:
            text += "..."
        return text

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
