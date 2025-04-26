import subprocess
import os
from typing import Dict, List
from vibecoder.tools.base import Tool

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")

class GitTool(Tool):
    name = "git_tool"
    supported_commands = ["status", "log", "diff", "show", "grep"]

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
                            "description": "The git command to execute (e.g., 'status', 'log', 'diff')."
                        },
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Options to pass to the git command (e.g., ['--since=2.weeks'])."
                        },
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "File paths or patterns the command should consider."
                        }
                    },
                    "required": ["command"]
                }
            }
        }

    def run(self, args: Dict) -> str:
        command = args.get("command")
        if command not in self.supported_commands:
            return f"Error: Attempted to use unsupported git command {command}. Only [{', '.join(self.supported_commands)}] are supported"
        options = args.get("options", [])
        paths = args.get("paths", [])

        git_command = ["git", command] + options + paths

        try:
            result = subprocess.run(git_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                return f"Error: {result.stderr.decode('utf-8')}"
            return result.stdout.decode('utf-8')
        except Exception as e:
            return f"[Error executing git command '{' '.join(git_command)}': {e}]"
