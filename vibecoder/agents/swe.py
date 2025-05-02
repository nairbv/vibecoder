import os
import pathlib

from dotenv import load_dotenv
from jinja2 import Template
from openai import AsyncOpenAI

import vibecoder.tools
from vibecoder.agents.agent import Agent

PROMPTS_DIR = pathlib.Path(__file__).parent.parent / "prompts"

load_dotenv()

# Initialize client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=0)


def build_swe_agent() -> Agent:
    tools = vibecoder.tools.get_all_tools()

    tool_descriptions = "\n".join(t.display_signature for t in tools)

    swe_prompt_path = PROMPTS_DIR / "swe.md"
    with open(swe_prompt_path, "r") as f:
        swe_template = Template(f.read())

    system_prompt = swe_template.render(tools=tool_descriptions)

    # Pass the client to the Agent
    return Agent(
        client,
        system_prompt=system_prompt.strip(),
        tools={tool.name: tool for tool in tools},
    )
