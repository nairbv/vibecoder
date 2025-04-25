from abc import ABC, abstractmethod
from typing import Dict

class Tool(ABC):
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
    def run(self, args: Dict) -> str:
        pass

    @property
    def display_signature(self) -> str:
        """Generate a human-readable summary of the tool's signature."""
        sig = self.signature["function"]
        params = sig.get("parameters", {}).get("properties", {})
        required = set(sig.get("parameters", {}).get("required", []))

        param_strs = []
        for param_name, param_info in params.items():
            param_type = param_info.get("type", "str")
            if param_name in required:
                default = ""
            else:
                default = " = None"
            param_strs.append(f"{param_name}: {param_type}{default}")

        param_list = ", ".join(param_strs)
        return f"{sig['name']}({param_list})"
