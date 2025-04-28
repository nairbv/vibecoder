from vibecoder.tools.base import Tool
import os
import subprocess
from typing import Dict


PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")

class ApplyDiffPatchTool(Tool):
    name="apply_diff_patch"

    def __init__(self):
        super().__init__()

    @property
    def prompt_description(self) -> str:
        path = os.path.join(PROMPT_DIR, "apply_diff_patch.md")
        with open(path, "r") as f:
            return f.read().strip()

    @property
    def signature(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Apply a patch to files using a standard `.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patch_text": {
                            "type": "string",
                            "description": "The unified patch text to apply.",
                        },
                    },
                    "required": ["patch_text"],
                },
            }
        }


    def run(self, args: Dict) -> str:
        """Apply the patch text using the `patch` command and return all output."""
        patch_text = args.get("patch_text")
        if not patch_text:
            return "[Error: Missing 'patch_text' argument.]"

        try:
            result = subprocess.run(
                ['patch', '-f', '-t', '-p0'],
                input=patch_text,
                capture_output=True,
                text=True,
                check=False,
            )
            output_summary = f"[Patch Command Exit Code: {result.returncode}]\n"

            if result.stdout.strip():
                output_summary += f"\n[STDOUT]\n{result.stdout.strip()}\n"
            if result.stderr.strip():
                output_summary += f"\n[STDERR]\n{result.stderr.strip()}\n"

            if result.returncode != 0:
                return f"[Patch application failed]\n{output_summary.strip()}"
            else:
                return f"[Patch applied successfully]\n{output_summary.strip()}"

        except Exception as e:
            return f"[Unexpected error during patch application: {str(e)}]"

