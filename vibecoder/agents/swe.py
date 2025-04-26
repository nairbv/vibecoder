from openai import AsyncOpenAI
from vibecoder.agents.agent import Agent
from vibecoder.tools.read_file import ReadFileTool
from vibecoder.tools.tree_files import TreeFilesTool
from vibecoder.tools.write_file import WriteFileTool
from vibecoder.tools.apply_patch import ApplyPatchTool
from vibecoder.tools.pytest_tool import PytestTool
from vibecoder.tools.git_tool import GitTool
from vibecoder.tools.grep import GrepTool

from jinja2 import Template
import pathlib
import os

PROMPTS_DIR = pathlib.Path(__file__).parent.parent / "prompts"


# Initialize client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=0)

def build_swe_agent() -> Agent:
    tools = [
        ReadFileTool(),
        WriteFileTool(),
        TreeFilesTool(),
        ApplyPatchTool(),
        PytestTool(),
        GrepTool(),
        GitTool(),
    ]

    tool_descriptions = "\n".join(t.display_signature for t in tools)

    swe_prompt_path = PROMPTS_DIR / "swe.md"
    with open(swe_prompt_path, "r") as f:
        swe_template = Template(f.read())

    system_prompt = swe_template.render(tools=tool_descriptions)

    # Pass the client to the Agent
    return Agent(system_prompt=system_prompt.strip(), tools={tool.name: tool for tool in tools}, client=client)
