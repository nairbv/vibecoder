import asyncio
import os
import sys
import threading
import traceback

import click
from dotenv import load_dotenv
from prompt_toolkit import Application
from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.containers import VSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.scrollable_pane import ScrollOffsets
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea

from vibecoder import agents
from vibecoder.agent_status import RespondingStatus, WaitingStatus, WorkingStatus
from vibecoder.agents import AgentResponse, ToolUse
from vibecoder.agents.agent import ToolResult
from vibecoder.agents.mock_agent import MockAgent
from vibecoder.agents.swe import build_anthropic_swe_agent, build_swe_agent

HISTORY_FILE = os.path.expanduser("~/.vibecoder_history")


def load_env():
    if os.path.exists(".env"):
        load_dotenv()
    else:
        print("Warning: .env file not found, OPENAI_API_KEY may not be set.")


class REPLContextManager:
    def __init__(self):
        load_env()
        self.agent = build_swe_agent()
        self.agent_type = "swe"
        self.agents_dict = {
            "swe": self.agent,
            "mock": None,  # Initialized to None; will instantiate upon first switch
            "anthropic": None,
            "analyst": None,
        }
        self.last_output = []
        self._working = False
        self._interrupted = False
        self._restart_after_edit = None
        self._status_task = None
        self.status = WaitingStatus()
        self.status_bar = TextArea(
            style="class:status",
            focusable=False,
            height=1,
            read_only=True,
            text="Status: Ready",
        )
        self._output_lines = []
        self._scroll_pos = None
        self._create_application()

    def _create_application(self):
        try:
            if not self._output_lines:
                self._output_lines.append(("assist", "🤖 vibecoder is starting...\n"))
            self.output_control = FormattedTextControl(
                text=lambda: [
                    (f"class:{style}", line) for style, line in self._output_lines
                ],
                focusable=True,
                get_cursor_position=self._get_output_cursor_position,
            )
            self.output_control.preferred_height = (
                lambda width, height, ui_content, config: len(self._output_lines)
            )

            self.output_window = Window(
                content=self.output_control,
                style="class:output",
                wrap_lines=True,
                right_margins=[ScrollbarMargin(display_arrows=True)],
                height=Dimension(weight=1),
                always_hide_cursor=True,
                scroll_offsets=ScrollOffsets(top=3, bottom=3),
            )
            self.input_window = TextArea(
                style="class:input",
                prompt="💬 $ ",
                height=1,
                multiline=False,
                wrap_lines=False,
                accept_handler=self.on_enter,
                history=FileHistory(HISTORY_FILE),
            )
            self.layout = Layout(
                HSplit(
                    [
                        self.status_bar,
                        self.output_window,
                        Window(height=1, char="-"),  # Separator line
                        self.input_window,
                    ]
                ),
                focused_element=self.input_window,
            )
            self.kb = KeyBindings()
            self.kb.add("c-c")(self.handle_ctrl_c)
            self.kb.add("pageup")(self.handle_pageup)
            self.kb.add("pagedown")(self.handle_pagedown)
            self.style = Style.from_dict(
                {
                    "output": "bg:#000000 #ffffff",  # default for output text box. text responses from agent (white on black)
                    "input": "bg:#222222 #00ff00",  # input text box (dark grey, green text)
                    "status": "bg:#444444 #ffffff bold",  # status bar at top of window (grey background, white text)
                    "toolcall": "ansicyan",  # tool calls from the agent (cyan)
                    "usermsg": "ansigreen",  # message from the user (green)
                    "application": "bold #ffffff",  # application messages like commands and exceptions (bold white)
                }
            )
            self.app = Application(
                layout=self.layout,
                key_bindings=self.kb,
                style=self.style,
                full_screen=True,
            )
        except Exception as e:
            print(e, file=sys.stderr)
            self.print(e)

    def _get_output_cursor_position(self):
        y = self._scroll_pos or len(self._output_lines) - 1
        return Point(0, y)

    def print(self, text: str, style: str = "application"):
        split = text.rstrip().splitlines()
        for line in split:
            self._output_lines.append((style, line + "\n"))
        get_app().invalidate()

    def on_enter(self, buffer):
        try:
            text = buffer.text
            text = text.strip()
            if text:
                self.input_window.buffer.history.append_string(text)
                self.print(f"💬 $ {text}", style="usermsg")
                asyncio.create_task(self.handle_line(text))
            buffer.text = ""
        except Exception as e:
            tb = traceback.format_exc()
            self.print(f"⚠️ Exception occurred:\n{tb}")
            if text == "/quit":
                exit()

    async def run(self):
        while True:
            try:
                await self.app.run_async()
            except Exception as e:
                print(f"⚠️ Critical failure: {e}")
                break
            if not self._restart_after_edit:
                break
            self._restart_after_edit = None
            self._create_application()

    async def handle_line(self, line: str):
        try:
            if line.startswith("/"):
                await self.handle_command(line[1:].strip())
            else:
                self.update_status(RespondingStatus())
                await self.ask(line)
                self.update_status(WaitingStatus())
        except Exception as e:
            tb = traceback.format_exc()
            self.print(f"⚠️ Exception occurred:\n{tb}")

    async def handle_command(self, command: str):
        if command in {"quit", "exit"}:
            self.print("👋 Exiting vibecoder.")
            self.app.exit()
        elif command == "edit":
            await self.open_editor_and_ask()
        elif command.startswith("work"):
            await self.start_working(command)
        elif command.startswith("save"):
            user_instruction = command[
                4:
            ].strip()  # Extract user instructions after /save
            await self.save_context(user_instruction)
        elif command == "interrupt":
            self._interrupted = True
            self.print("🛑 Interrupt signal sent. Will yield at next pause.")
        elif command.startswith("role"):
            await self.switch_role(command[5:].strip())
        elif command.startswith("model"):
            model_name = command[5:].strip()
            if not model_name:
                self.print(f"Current model: {self.agent.model}")
            else:
                self.agent.set_model(model_name)
                self.print(f"✅ Model set to {model_name}.")
        else:
            self.print(f"⚠️ Unknown command: /{command}")

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
        outputs = []
        try:
            async for part in self.agent.ask(summary_request):
                outputs.append(part)
            summary = "\n".join(outputs)
        except Exception as e:
            self.print(f"⚠️ Error gathering async generator output: {str(e)}")
            return
        with open(session_file, "w") as file:
            file.write(summary)
        self.print("✅ Context successfully saved.")

    async def switch_role(self, role: str):
        role = role.lower()
        if role == self.agent_type:
            self.print(f"🤖 Already using {role} agent.")
            return
        if role in self.agents_dict:
            if not self.agents_dict[role]:
                self.agents_dict[role] = agents.create_agent_by_role(role)
            self.agent = self.agents_dict[role]
            self.agent_type = role
        else:
            self.print(f"⚠️ Unknown agent role: {role}")
            return
        self.print(f"✅ Switched to {role} agent.")

    async def ask(self, line: str):
        try:
            outputs = []
            async for output in self.agent.ask(line):
                if isinstance(output, AgentResponse):
                    text = f"🤖 SWE: {output.content}"
                    self.print(text, style="output")
                    outputs.append(text)
                elif isinstance(output, ToolUse):
                    args_str = str(output.arguments)
                    if len(args_str) > 200:
                        args_str = args_str[:200] + "..."
                    tool_call_str = f"{output.tool_name}({args_str})"
                    text = f"🔧 Tool call: {tool_call_str}"
                    self.print(text, style="toolcall")
                    outputs.append(text)
                elif isinstance(output, ToolResult):
                    cleaned = output.content.strip().replace("\n", "\\n")
                    text = cleaned[:100]
                    if len(cleaned) >= 100:
                        text += "..."
                    self.print(
                        f"ToolResult({output.tool_name}): {text}", style="toolcall"
                    )
                else:
                    self.print(f"unexpected response from agent: '{str(output)}'")
            self.last_output = outputs
        except Exception as e:
            tb = traceback.format_exc()
            self.print(f"⚠️ Exception during ask:\n{tb}")

    async def open_editor_and_ask(self):
        template = self._prepare_editor_template()
        loop = asyncio.get_running_loop()
        edited_text = await loop.run_in_executor(
            None, self._open_editor_blocking, template
        )
        if edited_text:
            self.print(f"💬 $ {edited_text}", style="usermsg")
            self.input_window.buffer.history.append_string(edited_text)
            await self.ask(edited_text)
        self._restart_after_edit = True
        self.app.exit()

    def _open_editor_blocking(self, template_text: str) -> str:
        edited_text = click.edit(text=template_text)
        if edited_text is None:
            return ""
        stripped = "\n".join(
            line
            for line in edited_text.splitlines()
            if not line.lstrip().startswith("#")
        )
        return stripped.strip()

    async def start_working(self, command: str):
        try:
            parts = command.split()
            minutes = int(parts[1]) if len(parts) > 1 else 1
        except Exception:
            minutes = 1
        self.print(f"⚡ Entering autonomous work mode for {minutes} minutes...")
        self.status = WorkingStatus(duration=minutes * 60)
        self._working = True
        self._interrupted = False
        end_time = asyncio.get_event_loop().time() + (minutes * 60)
        continue_msg = "Do what you think is best. Keep going until you've solved the problem. Think carefully, brainstorm, and consider your tools if you get stuck."
        while (
            self._working
            and not self._interrupted
            and asyncio.get_event_loop().time() < end_time
        ):
            self.print(f"💬 $ {continue_msg}", style="usermsg")
            await self.ask(continue_msg)
        self.status = WaitingStatus()
        self.print("✅ Finished autonomous work mode.")

    def _prepare_editor_template(self) -> str:
        if not len(self.last_output):
            return ""
        return (
            "\n\n\n\n\n" + "\n".join(f"# {line}" for line in self.last_output) + "\n\n"
        )

    def handle_ctrl_c(self, event):
        self._interrupted = True
        self.print("🛑 Ctrl+C interrupt received.")
        event.app.exit()

    def handle_pageup(self, event):
        pos = self._scroll_pos
        if pos is None:
            pos = len(self._output_lines) - 1
        pos -= 20
        if pos < 1:
            pos = 1
        self._scroll_pos = pos
        self.app.invalidate()

    def handle_pagedown(self, event):
        if self._scroll_pos is None:
            return
        pos = self._scroll_pos
        pos += 20
        if pos >= len(self._output_lines) - 1:
            pos = None
        self._scroll_pos = pos
        self.app.invalidate()

    def update_status(self, status):
        self.status = status
        self.status_bar.text = f"Status: {self.status.status_line()}"
        self.status_bar.buffer.cursor_position = 0
        should_animate = self.status.is_busy()
        if should_animate:
            if self._status_task is None or self._status_task.cancelled():
                self._status_task = asyncio.create_task(self.start_status_animation())
        else:
            if self._status_task:
                self._status_task.cancel()

    async def start_status_animation(self):
        animation_frames = ["|", "/", "-", "\\"]
        idx = 0
        while True:
            self.status_bar.text = (
                f"Status: {self.status.status_line()} - {animation_frames[idx]}"
            )
            self.status_bar.buffer.cursor_position = 0
            idx = (idx + 1) % len(animation_frames)
            await asyncio.sleep(0.5)


def main():
    repl = REPLContextManager()
    asyncio.run(repl.run())


if __name__ == "__main__":
    main()
