import json
import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv

from vibecoder.tools.base import Tool

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../prompts/tools")
description_path = os.path.join(PROMPT_DIR, "web_search.md")

load_dotenv()


class SearchTool(Tool):
    name = "web_search"
    _SUPPORTED_ENGINES = ["brave"]
    _BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"
    _MAX_RESULTS = 20

    @property
    def prompt_description(self) -> str:
        with open(description_path, "r") as f:
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
                        "query": {
                            "type": "string",
                            "description": "The search query to perform.",
                        },
                        "engine": {
                            "type": "string",
                            "enum": self._SUPPORTED_ENGINES,
                            "default": "brave",
                            "description": "The search engine to use (currently only 'brave' is supported).",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of results to return (default 5, max 20).",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    def do_search(self, args: Dict[str, Any]) -> dict:
        engine = args.get("engine", "brave")
        if engine not in self._SUPPORTED_ENGINES:
            raise Exception(
                f"Engine '{engine}' not supported. Supported engines: {self._SUPPORTED_ENGINES}"
            )

        if engine == "brave":
            brave_key = os.getenv("BRAVE_API_KEY")
            if not brave_key:
                raise Exception(
                    "API key not set in environment variable BRAVE_API_KEY."
                )
            query = args.get("query")
            count = args.get("count", 5)
            if not isinstance(count, int) or not (1 <= count <= self._MAX_RESULTS):
                count = min(max(1, int(count)), self._MAX_RESULTS)
            headers = {"Accept": "application/json", "X-Subscription-Token": brave_key}
            params = {"q": query, "count": count}
            resp = requests.get(
                self._BRAVE_API_URL, headers=headers, params=params, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for idx, item in enumerate(data.get("web", {}).get("results", [])):
                results.append(
                    {
                        "rank": idx + 1,
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "summary": item.get("description", ""),
                    }
                )
            return results
        else:
            raise Exception(f"Unexpected engine {engine}")

    def run(self, args: Dict[str, Any]) -> str:
        try:
            query = args.get("query")
            results = self.do_search(args)
            return _format_search_results_for_prompt(query, results)
        except Exception as e:
            return f"[Error in web search] {e}"


def _format_search_results_for_prompt(query, results: list[dict]) -> str:
    """Format Brave search results for inclusion in a ChatGPT prompt."""
    output = []
    output.append(f"## Search results for: {query}")
    if not results:
        output.append("No results found.")
    for item in results:
        output.append(
            f"- ({item['rank']}) [{item['title']}]({item['url']})\n  {item['summary']}"
        )
    output.append("")  # add spacing
    return "\n".join(output)
