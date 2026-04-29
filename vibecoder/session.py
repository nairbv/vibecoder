import asyncio
import os
import traceback
from typing import Callable, Optional

from vibecoder import agents
from vibecoder.agent_status import (
    AgentStatus,
    RespondingStatus,
    WaitingStatus,
    WorkingStatus,
)
from vibecoder.agents.agent import BaseAgent
from vibecoder.messages import AgentResponse, ToolResult, ToolUse


class Session:
    """Core business logic for vibecoder, decoupled from any UI."""

    def __init__(
        self,
        on_output: Callable[[str, str], None],
        on_status: Callable[[AgentStatus], None],
        on_exit: Callable[[], None],
        agent_factory: Callable[[str], BaseAgent] = None,
        default_role: str = "swe",
    ):
        self.on_output = on_output
        self.on_status = on_status
        self.on_exit = on_exit
        self.agent_factory = agent_factory or agents.create_agent_by_role

        self.agent: BaseAgent = self.agent_factory(default_role)
        self.agent_type: str = default_role
        self.agents_dict: dict[str, Optional[BaseAgent]] = {
            default_role: self.agent,
            "swe": None,
            "mock": None,
            "anthropic": None,
            "analyst": None,
        }
        # Ensure the default role entry points to the created agent
        self.agents_dict[default_role] = self.agent

        self.last_output: list[str] = []
        self.status: AgentStatus = WaitingStatus()
        self._working: bool = False
        self._interrupted: bool = False

    def output(self, text: str, style: str = "application"):
        self.on_output(text, style)

    async def handle_line(self, line: str):
        try:
            if line.startswith("/"):
                await self.handle_command(line[1:].strip())
            else:
                self.on_status(RespondingStatus())
                await self.ask(line)
                self.on_status(WaitingStatus())
        except Exception:
            tb = traceback.format_exc()
            self.output(f"⚠️ Exception occurred:\n{tb}")

    async def handle_command(self, command: str):
        if command in {"quit", "exit"}:
            self.output("👋 Exiting vibecoder.")
            self.on_exit()
        elif command.startswith("work"):
            await self.start_working(command)
        elif command.startswith("save"):
            user_instruction = command[4:].strip()
            await self.save_context(user_instruction)
        elif command == "interrupt":
            self._interrupted = True
            self.output("🛑 Interrupt signal sent. Will yield at next pause.")
        elif command.startswith("role"):
            await self.switch_role(command[4:].strip())
        elif command.startswith("model"):
            model_name = command[5:].strip()
            if not model_name:
                self.output(f"Current model: {self.agent.model}")
            else:
                self.agent.set_model(model_name)
                self.output(f"✅ Model set to {model_name}.")
        else:
            self.output(f"⚠️ Unknown command: /{command}")

    async def ask(self, line: str):
        try:
            outputs = []
            async for msg in self.agent.ask(line):
                if isinstance(msg, AgentResponse):
                    text = f"🤖 SWE: {msg.content}"
                    self.output(text, style="output")
                    outputs.append(text)
                elif isinstance(msg, ToolUse):
                    args_str = str(msg.arguments)
                    if len(args_str) > 200:
                        args_str = args_str[:200] + "..."
                    tool_call_str = f"{msg.tool_name}({args_str})"
                    text = f"🔧 Tool call: {tool_call_str}"
                    self.output(text, style="toolcall")
                    outputs.append(text)
                elif isinstance(msg, ToolResult):
                    cleaned = msg.content.strip().replace("\n", "\\n")
                    text = cleaned[:100]
                    if len(cleaned) >= 100:
                        text += "..."
                    self.output(
                        f"ToolResult({msg.tool_name}): {text}", style="toolcall"
                    )
                else:
                    self.output(f"unexpected response from agent: '{str(msg)}'")
            self.last_output = outputs
        except Exception:
            tb = traceback.format_exc()
            self.output(f"⚠️ Exception during ask:\n{tb}")

    async def switch_role(self, role: str):
        role = role.lower()
        if role == self.agent_type:
            self.output(f"🤖 Already using {role} agent.")
            return
        if role in self.agents_dict:
            if not self.agents_dict[role]:
                self.agents_dict[role] = self.agent_factory(role)
            self.agent = self.agents_dict[role]
            self.agent_type = role
        else:
            self.output(f"⚠️ Unknown agent role: {role}")
            return
        self.output(f"✅ Switched to {role} agent.")

    async def save_context(self, user_text: str):
        prompt_path = "vibecoder/prompts/save_context.md"
        session_file = ".vibecoder/swe_session.md"
        if not os.path.exists(".vibecoder"):
            os.makedirs(".vibecoder")
        with open(prompt_path, "r") as file:
            prompt = file.read()
        if user_text:
            user_instruction = f"User instruction: {user_text}\n"
        else:
            user_instruction = ""
        summary_request = f"{prompt}\n{user_instruction}"
        parts = []
        try:
            async for part in self.agent.ask(summary_request):
                if isinstance(part, AgentResponse):
                    parts.append(part.content)
            summary = "\n".join(parts)
        except Exception as e:
            self.output(f"⚠️ Error gathering async generator output: {str(e)}")
            return
        with open(session_file, "w") as file:
            file.write(summary)
        self.output("✅ Context successfully saved.")

    async def start_working(self, command: str):
        try:
            cmd_parts = command.split()
            minutes = int(cmd_parts[1]) if len(cmd_parts) > 1 else 1
        except Exception:
            minutes = 1
        self.output(f"⚡ Entering autonomous work mode for {minutes} minutes...")
        self.on_status(WorkingStatus(duration=minutes * 60))
        self._working = True
        self._interrupted = False
        end_time = asyncio.get_event_loop().time() + (minutes * 60)
        continue_msg = "Do what you think is best. Keep going until you've solved the problem. Think carefully, brainstorm, and consider your tools if you get stuck."
        while (
            self._working
            and not self._interrupted
            and asyncio.get_event_loop().time() < end_time
        ):
            await asyncio.sleep(0)
            self.output(f"💬 $ {continue_msg}", style="usermsg")
            await self.ask(continue_msg)
        self.on_status(WaitingStatus())
        self.output("✅ Finished autonomous work mode.")
