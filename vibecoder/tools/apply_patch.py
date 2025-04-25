import os
from typing import Dict
from vibecoder.tools.base import Tool
from vibecoder.tools import apply_patch_lib

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")

class ApplyPatchTool(Tool):
    name = "apply_patch"

    @property
    def prompt_description(self) -> str:
        path = os.path.join(PROMPT_DIR, "apply_patch.md")
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
                        "input": {
                            "type": "string",
                            "description": " The apply_patch command that you wish to execute."
                        }
                    },
                    "required": ["input"]
                }
            }
        }

    def run(self, args: Dict) -> str:
        patch_text = args.get("input")
        if not patch_text:
            return "[Error: Missing 'input' (patch text).]"

        try:
            result = apply_patch_lib.process_patch(
                text=patch_text,
                open_fn=apply_patch_lib.open_file,
                write_fn=apply_patch_lib.write_file,
                remove_fn=apply_patch_lib.remove_file,
            )
            return result
        except apply_patch_lib.DiffError as e:
            return f"[Patch application failed: {e}]"
        except Exception as e:
            return f"[Unexpected error during patch: {e}]"
