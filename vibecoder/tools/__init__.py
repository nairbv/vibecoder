import importlib
import os
from typing import List

from vibecoder.tools.base import Tool
from vibecoder.tools.fetch_url import FetchUrlTool
from vibecoder.tools.web_search import SearchTool

TOOLS_DIR = os.path.dirname(__file__)


def get_all_tools() -> List[Tool]:
    tool_instances = []
    tools = [
        f.split(".")[0]
        for f in os.listdir(TOOLS_DIR)
        if f.endswith(".py") and f not in ("__init__.py", "base.py")
    ]

    for tool in tools:
        module = importlib.import_module(f"vibecoder.tools.{tool}")
        for attr in dir(module):
            obj = getattr(module, attr)
            if isinstance(obj, type) and issubclass(obj, Tool) and obj is not Tool:
                tool_instances.append(obj())
    return tool_instances


def get_analyst_tools() -> List[Tool]:
    analyst_tool_names = {
        "grep",
        "git_tool",
        "read_file",
        "write_file",
        "tree_files",
        "pytest",
    }
    all_tools = get_all_tools()
    return [tool for tool in all_tools if tool.name in analyst_tool_names]


def get_chatbot_tools() -> List[Tool]:
    return [
        SearchTool(),
        FetchUrlTool(),
    ]
