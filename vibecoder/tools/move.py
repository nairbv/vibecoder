import os
from vibecoder.tools.base import Tool

class MoveTool(Tool):
    def __init__(self):
        self.name = "move_tool"

    @property
    def signature(self) -> dict:
        return {
            "function": {
                "name": "move",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string", "description": "The path of the file or directory to be moved."},
                        "destination": {"type": "string", "description": "The target path for the file or directory."}
                    },
                    "required": ["origin", "destination"]
                }
            }
        }

    @property
    def prompt_description(self) -> str:
        return "Use this tool to move or rename files within the workspace."

    def run(self, args: dict) -> str:
        origin = args.get("origin")
        destination = args.get("destination")
        
        # Sanitize inputs
        if not origin or not destination:
            return "Both 'origin' and 'destination' paths are required."
        if origin.startswith('/') or destination.startswith('/') or '..' in origin.split(os.sep) or '..' in destination.split(os.sep):
            return "Paths must be relative and confined to the working directory."

        # Ensure both paths are within the confines of the current directory
        root_dir = os.getcwd()
        origin_path = os.path.join(root_dir, origin)
        destination_path = os.path.join(root_dir, destination)

        try:
            os.rename(origin_path, destination_path)
            return f"Successfully moved from {origin} to {destination}."
        except FileNotFoundError:
            return f"The file or directory '{origin}' was not found."
        except Exception as e:
            return f"An error occurred: {e}."
