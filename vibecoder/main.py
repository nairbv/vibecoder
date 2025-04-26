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
        self._restart_after_edit = None
        self._status_task = None
        self.status_bar = TextArea(
            style="class:status",
            focusable=False,
            height=1,
            read_only=True,
            text="Status: Ready"
        )
        self._create_application()

    def _create_application(self):
        if hasattr(self, "output_window"):
            output = self.output_window.text
        else:
            output = "🤖 vibecoder is starting...\n"

        self.output_window = TextArea(
            style="class:output",
            focusable=False,
            scrollbar=True,
            wrap_lines=True,
            read_only=True,
            text=output,
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
            HSplit([
                self.status_bar,
                self.output_window,
                Window(height=1, char="-"),  # Separator line
                self.input_window,
            ]),
        )

        self.kb = KeyBindings()
        self.kb.add("c-c")(self.handle_ctrl_c)
        self.kb.add("pageup")(self.handle_pageup)
        self.kb.add("pagedown")(self.handle_pagedown)

        self.style = Style.from_dict({
            "output": "bg:#111111 #ffffff",
            "input": "bg:#222222 #00ff00",
            "status": "bg:#444444 #ffffff bold",
        })

        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=self.style,
            full_screen=True,
        )

    async def run(self):
        while True:
            try:
                await self.app.run_async()
            except Exception as e:
                self.print(f"⚠️ Critical failure: {e}")
                break

            if not self._restart_after_edit:
                break

            self._restart_after_edit = None

            self._create_application()

    def on_enter(self, buffer):
        try:
            text = buffer.text
            text = text.strip()
            if text:
                self.input_window.buffer.history.append_string(text)
                self.print(f"💬 $ {text}")
                asyncio.create_task(self.handle_line(text))
            buffer.text = ""

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
                self.update_status("💭 Thinking...", animate=True)  # Update status
                await self.ask(line)
                self.update_status("👂 Waiting for input...", animate=False)  # Revert
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
        # Use run_in_executor to open an editor without blocking the event loop
        loop = asyncio.get_running_loop()
        edited_text = await loop.run_in_executor(None, self._open_editor_blocking, template)

        if edited_text:
            self.print(f"💬 $ {edited_text}")
            self.input_window.buffer.history.append_string(edited_text)
            await self.ask(edited_text)

        # After finishing the ask, request an application restart
        self._restart_after_edit = True
        self.app.exit()

    def _open_editor_blocking(self, template_text: str) -> str:
        """ Blocking call to open an editor using click """
        edited_text = click.edit(text=template_text)
        if edited_text is None:
            return ""
        stripped = "\n".join(
            line for line in edited_text.splitlines()
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

    def print(self, text: str):
        # self.output_window.buffer.insert_text(text + "\n", move_cursor=True)
        self.output_window.text += text + "\n"
        self.output_window.buffer.cursor_position = len(self.output_window.buffer.text)

    def handle_ctrl_c(self, event):
        self._interrupted = True
        self.print("🛑 Ctrl+C interrupt received.")

    def handle_pageup(self, event):
        buffer = self.output_window.buffer
        lines = buffer.text[:buffer.cursor_position].splitlines()
        lines_to_scroll = 20  # Scroll up about 20 lines
        new_line_index = max(0, len(lines) - lines_to_scroll)
        new_pos = sum(len(line) + 1 for line in lines[:new_line_index])  # +1 for each newline character
        buffer.cursor_position = new_pos

        # couldn't get this to work
        # window = self.output_window.window
        # if window and window.render_info:
        #     scroll_amount = window.render_info.window_height // 2  # Half a screen
        #     window.vertical_scroll = max(0, (window.vertical_scroll or 0) - scroll_amount)
        #     event.app.invalidate()

    def handle_pagedown(self, event):
        buffer = self.output_window.buffer
        lines = buffer.text[:buffer.cursor_position].splitlines()
        total_lines = buffer.text.count("\n")
        lines_to_scroll = 20  # Scroll down about 20 lines
        new_line_index = min(total_lines, len(lines) + lines_to_scroll)
        new_pos = sum(len(line) + 1 for line in buffer.text.splitlines()[:new_line_index])
        buffer.cursor_position = new_pos

        # couldn't get this to work
        # window = self.output_window.window
        # if window and window.render_info:
        #     scroll_amount = window.render_info.window_height // 2  # Half a screen
        #     max_scroll = window.render_info.content_height - window.render_info.window_height
        #     window.vertical_scroll = min(max_scroll, (window.vertical_scroll or 0) + scroll_amount)
        #     event.app.invalidate()

    def update_status(self, text, animate=False):
        # Properly replace the existing text
        self.status_bar.text = f"Status: {text}"
        self.status_bar.buffer.cursor_position = 0

        if animate:
            if self._status_task is None or self._status_task.cancelled():
                self._status_task = asyncio.create_task(self.start_status_animation())
        else:
            if self._status_task:
                self._status_task.cancel()

    async def start_status_animation(self):
        """Start a looping task to update the status bar for animations."""
        animation_frames = ['|', '/', '-', '\\']
        idx = 0
        while True:
            base_status = self.status_bar.text.partition(" - ")[0].replace("Status: ", "")
            self.update_status(f"{base_status} - {animation_frames[idx]}", animate=True)
            idx = (idx + 1) % len(animation_frames)
            await asyncio.sleep(0.5)


def main():
    repl = REPLContextManager()
    asyncio.run(repl.run())


if __name__ == "__main__":
    main()
