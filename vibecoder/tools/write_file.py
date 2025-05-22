import os
from typing import Dict

from vibecoder.messages import ToolResult, ToolUse
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
                            "description": "The path to the file to write",
                        },
                        "content": {
                            "type": "string",
                            "description": "The new contents to write into the file",
                        },
                        "append": {
                            "type": "boolean",
                            "description": "If true, append the content instead of overwriting.",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        }

    async def run_helper(self, args: Dict) -> str:
        path = args.get("path")
        content = args.get("content")
        append = args.get("append", False)

        if path is None or content is None:
            return "[Error: Missing 'path' or 'content' argument.]"

        try:
            directory = os.path.dirname(path)
            if directory:
                # Run blocking mkdir in thread pool
                await asyncio.to_thread(os.makedirs, directory, exist_ok=True)

            mode = "a" if append else "w"
            async with aiofiles.open(path, mode) as f:
                await f.write(content)

            return f"[Successfully wrote to '{path}']"

        except Exception as e:
            return f"[Error writing file '{path}': {e}]"

    async def run(self, tool_use: ToolUse) -> ToolResult:
        result_str = await self.run_helper(tool_use.arguments)
        return ToolResult(
            content=result_str,
            tool_name=self.name,
            tool_call_id=tool_use.tool_call_id,
        )
