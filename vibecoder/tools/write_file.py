import os
from typing import Dict
from vibecoder.tools.base import Tool

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")

class WriteFileTool(Tool):
    name = "write_file"

    @property
    def prompt_description(self) -> str:
        path = os.path.join(PROMPT_DIR, "write_file.md")
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
                            "description": "The path to the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "The new contents to write into the file"
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        }

    def run(self, args: Dict) -> str:
        path = args.get("path")
        content = args.get("content")

        if path is None or content is None:
            return "[Error: Missing 'path' or 'content' argument.]"

        try:
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            return f"[Successfully wrote to '{path}']"
        except Exception as e:
            return f"[Error writing file '{path}': {e}]"
