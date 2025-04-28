import os
import shlex
import subprocess
from typing import Dict

from .base import Tool

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")
description_path = os.path.join(PROMPT_DIR, "grep.md")


class GrepTool(Tool):
    name = "grep"

    @property
    def prompt_description(self) -> str:
        with open(description_path, "r") as f:
            return f.read().strip()

    @property
    def signature(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": "grep",
                "description": self.prompt_description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "The search pattern, supports regex.",
                        },
                        "paths": {"type": "array", "items": {"type": "string"}},
                        "ignore_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": [],
                        },
                        "include_pattern": {"type": "string", "default": None},
                        "ignore_case": {"type": "boolean", "default": False},
                    },
                    "required": ["pattern", "paths"],
                },
            },
        }

    def run(self, args: Dict) -> str:
        pattern = args["pattern"]
        paths = args["paths"]
        ignore_patterns = args.get("ignore_patterns", [])
        include_pattern = args.get("include_pattern")
        ignore_case = args.get("ignore_case", False)

        # Validate and sanitize inputs
        safe_paths = []
        for p in paths:
            if p.startswith("/") and "tmp" not in p:
                raise ValueError(f"Unsafe absolute path traversal: {p}")
            if ".." in p:
                raise ValueError(f"Unsafe relative path traversal: {p}")
            safe_paths.append(shlex.quote(p.rstrip("/")))

        if not safe_paths:
            return "[Error: No valid paths provided!]"

        # Prepare the grep command
        cmd = ["grep", "-r"]
        if ignore_case:
            cmd.append("-i")
        if include_pattern:
            cmd.extend(["--include", shlex.quote(include_pattern)])
        if ignore_patterns:
            for ip in ignore_patterns:
                cmd.append(f"--exclude={shlex.quote(ip)}")

        # Add the search pattern and paths
        cmd.append(shlex.quote(pattern))
        cmd.extend(safe_paths)

        # Execute the command
        result = subprocess.run(
            " ".join(cmd), shell=True, capture_output=True, text=True
        )

        return result.stdout if result.returncode in (0, 1) else result.stderr
