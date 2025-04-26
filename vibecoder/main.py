import os
import asyncio
import threading
import traceback
import click
from dotenv import load_dotenv
from prompt_toolkit import Application
from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.history import FileHistory
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.containers import VSplit
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.styles import Style

from vibecoder.agents.swe import build_swe_agent

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
        self.last_output = ""
        self._working = False
        self._interrupted = False

        self.output_window = TextArea(
            style="class:output",
            focusable=False,
            scrollbar=True,
            wrap_lines=True,
            read_only=True,
            text="🤖 vibecoder is starting...\n",
        )

        self.input_window = TextArea(
            style="class:input",
            prompt="💬 $ ",
            height=1,
            multiline=False,
            wrap_lines=False,
            accept_handler=self.on_enter,
            history=FileHistory(os.path.expanduser("~/.vibecoder_history")),
        )

        self.layout = Layout(
            HSplit([
                self.output_window,
                Window(height=1, char="-"),  # Separator line
                self.input_window,
            ])
        )

        self.kb = KeyBindings()
        self.kb.add("c-c")(self.handle_ctrl_c)

        self.style = Style.from_dict({
            "output": "bg:#111111 #ffffff",
            "input": "bg:#222222 #00ff00",
        })

        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=self.style,
            full_screen=True,
        )

    async def run(self):
        try:
            await self.app.run_async()
        except Exception as e:
            self.print(f"Critical failure: {e}")
            if self.app.is_running:
                self.app.exit()

    def on_enter(self, buffer):
        try:
            text = buffer.text
            buffer.text = ""

            if text.strip():
                self.input_window.buffer.history.append_string(text)
                self.print(f"💬 $ {text}")

            asyncio.create_task(self.handle_line(text))

        except Exception as e:
            tb = traceback.format_exc()
            self.print(f"⚠️ Exception occurred:\n{tb}")
            if text == "/quit":
                exit()

    async def handle_line(self, line: str):
        try:
            if line.startswith("/"):
                await self.handle_command(line[1:].strip())
            else:
                await self.ask(line)
        except Exception as e:
            tb = traceback.format_exc()
            self.print(f"⚠️ Exception occurred:\n{tb}")

    async def handle_command(self, command: str):
        if command in {"quit", "exit"}:
            self.print("👋 Exiting vibecoder.")
            await self.app.exit()
        elif command == "edit":
            await self.open_editor_and_ask()
        elif command.startswith("work"):
            await self.start_working(command)
        elif command == "interrupt":
            self._interrupted = True
            self.print("🛑 Interrupt signal sent. Will yield at next pause.")
        else:
            self.print(f"⚠️ Unknown command: /{command}")

    async def ask(self, line: str):
        try:
            outputs = []
            async for output in self.agent.ask(line):
                self.print(f"🤖 SWE: {output}")
                outputs.append(output)
            self.last_output = "\n".join(outputs)

        except Exception as e:
            tb = traceback.format_exc()
            self.print(f"⚠️ Exception during ask:\n{tb}")

    async def open_editor_and_ask(self):
        template = self._prepare_editor_template()
        edited_text = self._open_editor(template)
        if edited_text:
            self.print(f"💬 $ {edited_text}")
            await self.ask(edited_text)

    async def start_working(self, command: str):
        try:
            parts = command.split()
            minutes = int(parts[1]) if len(parts) > 1 else 1
        except Exception:
            minutes = 1

        self.print(f"⚡ Entering autonomous work mode for {minutes} minutes...")
        self._working = True
        self._interrupted = False
        end_time = asyncio.get_event_loop().time() + (minutes * 60)

        while self._working and not self._interrupted and asyncio.get_event_loop().time() < end_time:
            await self.ask("keep going")

        self._working = False
        self._interrupted = False
        self.print("✅ Finished autonomous work mode.")

    def _prepare_editor_template(self) -> str:
        if not self.last_output:
            return ""
        return "\n\n\n\n\n" + "\n".join(f"# {line}" for line in self.last_output.splitlines()) + "\n\n"

    def _open_editor(self, template_text: str) -> str:
        """Opens $EDITOR with optional template text, strips comment lines on return."""
        edited_text = click.edit(text=template_text)
        if edited_text is None:
            return ""
        stripped = "\n".join(
            line for line in edited_text.splitlines()
            if not line.lstrip().startswith("#")
        )
        return stripped.strip()

    def print(self, text: str):
        self.output_window.text += text + "\n"

    def handle_ctrl_c(self, event):
        self._interrupted = True
        self.print("🛑 Ctrl+C interrupt received.")


def main():
    repl = REPLContextManager()
    asyncio.run(repl.run())


if __name__ == "__main__":
    main()
