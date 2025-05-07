import os
from typing import Dict

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

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

    async def run(self, args: Dict) -> str:
        url = args.get("url")
        if not url:
            return "[Error: Missing 'url' argument.]"
        return await fetch_bs(url)


async def fetch_bs(url, min_words=5) -> str:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return f"[Error] Non-OK status code `{resp.status_code}`"
            html = resp.text
        return html_to_markdown(html, min_words=min_words)
    except httpx.RequestError as e:
        return f"[Error] {e}"


def html_to_markdown(html, min_words=5) -> str:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(
        ["script", "style", "footer", "nav", "aside", "noscript", "iframe", "form"]
    ):
        tag.decompose()

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
    for class_name in junk_classes:
        for tag in soup.find_all(
            class_=lambda c: c
            and any(
                cls.lower() == class_name for cls in (c if isinstance(c, list) else [c])
            )
        ):
            tag.decompose()

    for tag in soup.find_all(text=True):
        if tag.parent.name not in ["a", "p", "li", "span", "div", "section"]:
            continue
        if len(tag.strip().split()) < min_words:
            tag.extract()

    cleaned_html = soup.find("div", id="bodyContent") or soup.body or soup
    cleaned_html = str(cleaned_html)

    return md(cleaned_html, strip=["img", "video", "iframe"])
