import os
from typing import Dict

import aiofiles

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
                            "description": "The path to the file to read",
                        },
                        "start": {
                            "type": "integer",
                            "description": "Start reading the file from this line number (inclusive)",
                            "minimum": 0,
                        },
                        "end": {
                            "type": "integer",
                            "description": "Stop reading the file at this line number (exclusive)",
                            "minimum": 0,
                        },
                    },
                    "required": ["path"],
                },
            },
        }

    async def run(self, args: Dict) -> str:
        path = args.get("path")
        start = args.get("start")
        end = args.get("end")

        if not path:
            return "[Error: 'path' argument is required]"

        try:
            async with aiofiles.open(path, "r") as f:
                lines = await f.readlines()

            start = start or 0
            end = end or len(lines)

            # Validate and sanitize indices
            if not isinstance(start, int) or not isinstance(end, int):
                return "[Error: 'start' and 'end' must be integers]"

            start = max(0, start)
            end = min(len(lines), end)

            return "".join(lines[start:end])

        except Exception as e:
            return f"[Error reading file '{path}': {e}]"
