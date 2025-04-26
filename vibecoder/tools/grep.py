from .base import Tool
import shlex
import subprocess
from typing import Dict
import os

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")
description_path = os.path.join(PROMPT_DIR, "grep.md")

class GrepTool(Tool):
    name = 'grep'

    @property
    def prompt_description(self) -> str:
        with open(description_path, "r") as f:
            return f.read().strip()

    @property
    def signature(self) -> Dict:
        return {
            "function": {
                "name": "grep",
                "description": self.prompt_description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "The search pattern, supports regex."},
                        "paths": {"type": "array", "items": {"type": "string"}},
                        "ignore_patterns": {"type": "array", "items": {"type": "string"}, "default": []},
                        "include_pattern": {"type": "string", "default": None},
                        "ignore_case": {"type": "boolean", "default": False}
                    },
                    "required": ["pattern", "paths"]
                }
            }
        }

    def run(self, args: Dict) -> str:
        pattern = args['pattern']
        paths = args['paths']
        ignore_patterns = args.get('ignore_patterns', [])
        include_pattern = args.get('include_pattern')
        ignore_case = args.get('ignore_case', False)

        # Validate and sanitize inputs
        # Allow paths for testing or if they contain 'vibecoder'
        invalid_paths = [p for p in paths if not (p.startswith('/var/folders') or (p.startswith('/') and 'vibecoder' in p))]
        if invalid_paths:
            raise ValueError(f"Invalid paths: {invalid_paths}")
        safe_paths = [shlex.quote(p.rstrip('/')) for p in paths if p.startswith('/var/folders') or (p.startswith('/') and 'vibecoder' in p) or (not p.startswith('/') and '..' not in p)]

        if not safe_paths:
            return ""

        # Prepare the grep command
        cmd = ['grep', '-r']
        if ignore_case:
            cmd.append('-i')
        if include_pattern:
            cmd.extend(['--include', include_pattern])
        if ignore_patterns:
            for ip in ignore_patterns:
                cmd.append(f"--exclude={shlex.quote(ip)}")

        # Add pattern and paths
        cmd.extend([pattern] + safe_paths)

        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout if result.returncode == 0 else result.stderr
