import io
import sys
import os
import subprocess
from .base import Tool
from typing import Dict, List

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
                            "items": {"type": "string"},
                            "description": "List of test files or directories to run."
                        },
                        "verbose": {
                            "type": "boolean",
                            "description": "Run tests in verbose mode (show all tests).",
                            "default": False
                        },
                        "quiet": {
                            "type": "boolean",
                            "description": "Run tests quietly (only show minimal output).",
                            "default": False
                        },
                        "maxfail": {
                            "type": "integer",
                            "description": "Stop after this many failures. (Optional.)",
                        }
                    },
                    "required": ["paths"]
                }
            }
        }

    def run(self, args: Dict) -> str:
        paths: List[str] = args.get("paths", [])
        verbose: bool = args.get("verbose", False)
        quiet: bool = args.get("quiet", False)
        maxfail: int = args.get("maxfail", None)

        pytest_args = []

        if verbose:
            pytest_args.append("-v")
        if quiet:
            pytest_args.append("-q")
        if maxfail is not None:
            pytest_args.append(f"--maxfail={maxfail}")

        pytest_args += paths

        # Assemble the full command
        command = ["pytest"] + pytest_args

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False  # don't raise an exception even if tests fail
            )
        except Exception as e:
            return f"[Error running pytest: {e}]"

        result_text = f"Exit code: {result.returncode}\n\n"
        if result.stdout.strip():
            result_text += f"STDOUT:\n{result.stdout}\n"
        if result.stderr.strip():
            result_text += f"STDERR:\n{result.stderr}\n"

        return result_text.strip()
