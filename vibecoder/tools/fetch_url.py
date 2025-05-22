import os
from typing import Dict

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from vibecoder.messages import ToolResult, ToolUse
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

    async def run_helper(self, args: Dict) -> str:
        url = args.get("url")
        if not url:
            return "[Error: Missing 'url' argument.]"
        return await fetch_bs(url)

    async def run(self, tool_use: ToolUse) -> ToolResult:
        result_str = await self.run_helper(tool_use.arguments)
        return ToolResult(
            content=result_str,
            tool_name=self.name,
            tool_call_id=tool_use.tool_call_id,
        )


async def fetch_bs(url, min_words=5) -> str:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return f"[Error] Non-OK status code `{resp.status_code}` - {resp.text}"
            html = resp.text
        return html_to_markdown(html, min_words=min_words)
    except httpx.RequestError as e:
        return f"[Error] {e}"


def html_to_markdown(html: str, min_words: int = 2) -> str:
    soup = BeautifulSoup(html, "lxml")

    # 1. Drop obviously non-content elements
    for tag in soup(
        [
            "script",
            "style",
            "footer",
            "nav",
            "aside",
            "noscript",
            "iframe",
            "form",
            "figure",
            "table",
        ]
    ):
        tag.decompose()

    # 2. Wikipedia-specific junk
    for t in soup.select("sup.reference, span.mw-editsection, div.reflist"):
        t.decompose()

    # 3. Generic ad / banner classes
    junk_classes = [
        "header",
        "sidebar",
        "ads",
        "ad",
        "sponsored",
        "breadcrumb",
        "popup",
        "banner",
        "cookie",
        "subscribe",
    ]
    for cls in junk_classes:
        for t in soup.select(f".{cls}"):
            t.decompose()

    # 4. Remove tiny text fragments (but keep links & headings)
    for node in list(soup.strings):
        text = node.strip()
        parent = node.parent.name

        if not text:
            node.extract()
            continue

        # keep anchors & headings
        if parent in {
            "a",
            "strong",
            "b",
            "em",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "li",
        }:
            continue

        if len(text.split()) < min_words:
            node.extract()

    # 5. Pick the main content node (Wikipedia = #bodyContent)
    main = soup.find("div", id="bodyContent") or soup.body or soup
    return md(str(main), strip=["img", "video", "iframe"])
