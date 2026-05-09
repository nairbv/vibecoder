from abc import ABC, abstractmethod
from typing import Dict

from vibecoder.messages import ToolResult, ToolUse


class Tool(ABC):
    """
    Abstract base for tools. Subclasses must implement run(tool_use) returning ToolResult.
    """

    name: str

    @property
    @abstractmethod
    def prompt_description(self) -> str:
        """Returns a string used in system prompts to describe the tool."""
        pass

    @property
    @abstractmethod
    def signature(self) -> Dict:
        """Returns the OpenAI-style function signature."""
        pass

    @abstractmethod
    async def run(self, tool_use: ToolUse) -> ToolResult:
        """
        Execute the tool with a ToolUse object. Return the result wrapped in a ToolResult.
        """
        pass

    @property
    def canonical_schema(self) -> Dict:
        """Provider-neutral schema derived from `signature`.

        Returns a dict with keys: name, description, parameters
        (JSON-Schema). Used by vibecoder.clients to convert to each
        provider's wire format. Default impl extracts from the existing
        OpenAI-style `signature` so existing Tool subclasses do not need
        to change.
        """
        sig = self.signature
        if "function" in sig:
            fn = sig["function"]
            return {
                "name": fn.get("name", self.name),
                "description": fn.get("description", ""),
                "parameters": fn.get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            }
        return {
            "name": sig.get("name", self.name),
            "description": sig.get("description", ""),
            "parameters": sig.get("parameters", {"type": "object", "properties": {}}),
        }

    @property
    def display_signature(self) -> str:
        """Generate a human-readable summary of the tool's signature."""
        sig = self.signature["function"]
        params = sig.get("parameters", {}).get("properties", {})
        required = set(sig.get("parameters", {}).get("required", []))

        param_strs = []
        for param_name, param_info in params.items():
            param_type = param_info.get("type", "str")
            default = "" if param_name in required else " = None"
            param_strs.append(f"{param_name}: {param_type}{default}")

        param_list = ", ".join(param_strs)
        return f"{sig['name']}({param_list})"
