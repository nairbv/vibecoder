import os
from typing import Dict
from vibecoder.tools.base import Tool

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")

class ReadFileTool(Tool):
    name = "read_file"

    @property
    def prompt_description(self) -> str:
        path = os.path.join(PROMPT_DIR, "read_file.md")
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
                        "path": {
                            "type": "string",
                            "description": "The path to the file to read"
                        }
                    },
                    "required": ["path"]
                }
            }
        }

    def run(self, args: Dict) -> str:
        path = args.get("path")
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            return f"[Error reading file '{path}': {e}]"
