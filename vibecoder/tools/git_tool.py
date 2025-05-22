import asyncio
import os
from typing import Dict, List

from vibecoder.messages import ToolResult, ToolUse
from vibecoder.tools.base import Tool

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")


class GitTool(Tool):
    name = "git_tool"
    supported_commands = ["status", "log", "diff", "show", "grep", "checkout"]

    @property
    def prompt_description(self) -> str:
        path = os.path.join(PROMPT_DIR, "git_tool.md")
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
                        "command": {
                            "type": "string",
                            "description": f"The git command to execute. Available commands: {', '.join(self.supported_commands)}.",
                        },
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Options to pass to the git command (e.g., ['--since=2.weeks']).",
                        },
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "File paths or patterns the command should consider.",
                        },
                    },
                    "required": ["command"],
                },
            },
        }

    async def run_helper(self, args: Dict) -> str:
        command = args.get("command")
        if command not in self.supported_commands:
            return f"Error: Attempted to use unsupported git command '{command}'. Only [{', '.join(self.supported_commands)}] are supported"

        options = args.get("options", [])
        paths = args.get("paths", [])

        git_command = ["git", command] + options + paths

        try:
            proc = await asyncio.create_subprocess_exec(
                *git_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return f"Error: {stderr.decode().strip()}"
            return stdout.decode().strip()

        except Exception as e:
            return f"[Error executing git command '{' '.join(git_command)}': {e}]"

    async def run(self, tool_use: ToolUse) -> ToolResult:
        result_str = await self.run_helper(tool_use.arguments)
        return ToolResult(
            content=result_str,
            tool_name=self.name,
            tool_call_id=tool_use.tool_call_id,
        )
