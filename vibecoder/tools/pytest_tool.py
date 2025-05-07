import asyncio
import io
import os
import subprocess
import sys
from typing import Dict, List

from .base import Tool

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
                            "description": "List of test files or directories to run.",
                        },
                        "verbose": {
                            "type": "boolean",
                            "description": "Run tests in verbose mode (show all tests).",
                            "default": False,
                        },
                        "quiet": {
                            "type": "boolean",
                            "description": "Run tests quietly (only show minimal output).",
                            "default": False,
                        },
                        "maxfail": {
                            "type": "integer",
                            "description": "Stop after this many failures. (Optional.)",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds for the pytest run. Default 60, maximum 600.",
                            "default": 60,
                        },
                    },
                    "required": ["paths"],
                },
            },
        }

    async def run(self, args: Dict) -> str:
        paths: List[str] = args.get("paths", [])
        verbose: bool = args.get("verbose", False)
        quiet: bool = args.get("quiet", False)
        maxfail: int = args.get("maxfail", None)
        timeout_raw = args.get("timeout")

        default_timeout = 60
        max_timeout = 600

        if isinstance(timeout_raw, int):
            if timeout_raw <= 0:
                timeout = default_timeout
            elif timeout_raw > max_timeout:
                timeout = max_timeout
            else:
                timeout = timeout_raw
        else:
            timeout = default_timeout

        pytest_args = []

        if verbose:
            pytest_args.append("-v")
        if quiet:
            pytest_args.append("-q")
        if maxfail is not None:
            pytest_args.append(f"--maxfail={maxfail}")

        pytest_args += paths

        command = ["pytest"] + pytest_args

        try:
            proc = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()  # Clean up to avoid zombies
                return f"[Error: pytest run exceeded timeout of {timeout} seconds and was killed.]"

            result_text = f"Exit code: {proc.returncode}\n\n"
            if stdout and stdout.strip():
                result_text += f"STDOUT:\n{stdout.decode().strip()}\n"
            if stderr and stderr.strip():
                result_text += f"STDERR:\n{stderr.decode().strip()}\n"
            return result_text.strip()

        except Exception as e:
            return f"[Error running pytest: {e}]"
