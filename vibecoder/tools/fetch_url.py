import os
from typing import Dict

from vibecoder.tools.base import Tool

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")


class FetchUrlTool(Tool):
    name = "fetch_url"

    @property
    def prompt_description(self) -> str:
        path = os.path.join(PROMPT_DIR, "fetch_url.md")
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
                        "url": {
                            "type": "string",
                            "description": "The URL to fetch and extract content from.",
                        }
                    },
                    "required": ["url"],
                },
            },
        }

    def run(self, args: Dict) -> str:
        url = args.get("url")
        if not url:
            return "[Error: Missing 'url' argument.]"
        try:
            import trafilatura
        except ImportError:
            return "[Error: The trafilatura package is not installed.]"
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded is None:
                return f"[Error: Could not fetch content from URL: {url}]"
            extracted = trafilatura.extract(downloaded, include_links=True)
            if not extracted:
                return f"[Error: Content could not be extracted from {url}]"
            return extracted
        except Exception as e:
            return f"[Exception during fetch_url: {e}]"
