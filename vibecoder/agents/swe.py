import os
import pathlib

from dotenv import load_dotenv
from jinja2 import Template

import vibecoder.tools
from vibecoder.agents.agent import AnthropicAgent, OpenAIAgent

PROMPTS_DIR = pathlib.Path(__file__).parent.parent / "prompts"

load_dotenv()

# Initialize client


def build_swe_agent() -> OpenAIAgent:
    from openai import AsyncOpenAI

    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=0)

    tools = vibecoder.tools.get_all_tools()

    tool_descriptions = "\n".join(t.display_signature for t in tools)

    swe_prompt_path = PROMPTS_DIR / "swe.md"
    with open(swe_prompt_path, "r") as f:
        swe_template = Template(f.read())

    system_prompt = swe_template.render(tools=tool_descriptions)

    # Pass the client to the Agent
    return OpenAIAgent(
        openai_client,
        system_prompt=system_prompt.strip(),
        tools={tool.name: tool for tool in tools},
    )


def build_anthropic_swe_agent() -> OpenAIAgent:
    tools = vibecoder.tools.get_all_tools()

    tool_descriptions = "\n".join(t.display_signature for t in tools)

    swe_prompt_path = PROMPTS_DIR / "swe.md"
    with open(swe_prompt_path, "r") as f:
        swe_template = Template(f.read())

    system_prompt = swe_template.render(tools=tool_descriptions)

    from anthropic import AsyncAnthropic

    anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    return AnthropicAgent(
        anthropic_client,
        system_prompt=system_prompt.strip(),
        tools={tool.name: tool for tool in tools},
    )
