import os
from .base import Tool
import pytest
from typing import Dict

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")

class PytestTool(Tool):
    name = "pytest"

    @property
    def prompt_description(self) -> str:
        path = os.path.join(PROMPT_DIR, "pytest.md")
        with open(path, "r") as f:
            return f.read().strip()

    @property
    def signature(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.prompt_description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "paths": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Paths to test files or directories to run."
                        },
                        "options": {
                            "type": "string",
                            "description": "Additional pytest options (e.g., -q for quiet, -v for verbose).",
                            "default": ""
                        }
                    },
                    "required": ["paths"]
                }
            }
        }

    def run(self, args: Dict) -> str:
        paths = args.get("paths", [])
        options = args.get("options", "")
        # Use pytest's main function to execute tests programmatically
        result = pytest.main(paths + [options])
        return f"Pytest execution completed with result code: {result}"
