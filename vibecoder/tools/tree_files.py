import os
import shlex
import subprocess
from typing import Dict, List

from vibecoder.tools.base import Tool

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")


class TreeFilesTool(Tool):
    name = "tree_files"

    @property
    def prompt_description(self) -> str:
        path = os.path.join(PROMPT_DIR, "tree_files.md")
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
                            "description": "Root directory to list (default is '.'). Only subdirectories allowed.",
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Limit depth of recursion.",
                        },
                        "ignore_gitignore": {
                            "type": "boolean",
                            "description": "Respect .gitignore files when listing.",
                        },
                        "ignore_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Exclude files matching these patterns.",
                        },
                        "include_pattern": {
                            "type": "string",
                            "description": "Include only files matching this pattern.",
                        },
                        "show_modified_times": {
                            "type": "boolean",
                            "description": "Show last modified dates for each file.",
                        },
                        "show_directory_sizes": {
                            "type": "boolean",
                            "description": "Compute size of directories based on contents.",
                        },
                    },
                    "required": [],
                },
            },
        }

    def _sanitize_path(self, path: str) -> str:
        # Prevent accessing parent directories
        if ".." in path:
            path = path.replace("..", "")
        return path.strip()

    def run(self, args: Dict) -> str:
        cmd = ["tree"]

        # Path
        path = args.get("path", ".")
        path = self._sanitize_path(path)
        cmd.append(path)

        # Options
        if args.get("max_depth") is not None:
            cmd += ["-L", str(args["max_depth"])]

        if args.get("ignore_gitignore"):
            cmd.append("--gitignore")

        if args.get("ignore_patterns"):
            for pattern in args["ignore_patterns"]:
                safe_pattern = pattern.replace('"', '\\"')
                cmd += ["-I", safe_pattern]

        if args.get("include_pattern"):
            safe_pattern = args["include_pattern"].replace('"', '\\"')
            cmd += ["-P", safe_pattern]

        if args.get("show_modified_times"):
            cmd.append("-D")

        if args.get("show_directory_sizes"):
            cmd.append("--du")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"[tree command failed: {e.stderr.strip()}]"
        except Exception as e:
            return f"[Error running tree: {e}]"
