import asyncio
import os
import sys
import traceback

import click
from dotenv import load_dotenv
from prompt_toolkit import Application
from prompt_toolkit.application import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.scrollable_pane import ScrollOffsets
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea

from vibecoder.session import Session

HISTORY_FILE = os.path.expanduser("~/.vibecoder_history")


def load_env():
    if os.path.exists(".env"):
        load_dotenv()
    else:
        print("Warning: .env file not found, OPENAI_API_KEY may not be set.")


class REPLContextManager:
    def __init__(self, session: Session = None):
        load_env()
        self.last_output = []
        self._restart_after_edit = None
        self._status_task = None
        self._output_lines = []
        self._scroll_pos = None
        self._create_application()

        if session is not None:
            self.session = session
        else:
            self.session = Session(
                on_output=self.print,
                on_status=self.update_status,
                on_exit=lambda: self.app.exit(),
            )

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
            self.status_bar = TextArea(
                style="class:status",
                focusable=False,
                height=1,
                read_only=True,
                text="Status: Ready",
            )
            self.layout = Layout(
                HSplit(
                    [
                        self.status_bar,
                        self.output_window,
                        Window(height=1, char="-"),
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
                    "output": "bg:#000000 #ffffff",
                    "input": "bg:#222222 #00ff00",
                    "status": "bg:#444444 #ffffff bold",
                    "toolcall": "ansicyan",
                    "usermsg": "ansigreen",
                    "application": "bold #ffffff",
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
        split = str(text).rstrip().splitlines()
        for line in split:
            self._output_lines.append((style, line + "\n"))
        get_app().invalidate()

    def on_enter(self, buffer):
        try:
            text = buffer.text.strip()
            if text:
                self.input_window.buffer.history.append_string(text)
                self.print(f"💬 $ {text}", style="usermsg")
                if text == "/edit":
                    asyncio.create_task(self.open_editor_and_ask())
                else:
                    asyncio.create_task(self.session.handle_line(text))
            buffer.text = ""
        except Exception:
            tb = traceback.format_exc()
            self.print(f"⚠️ Exception occurred:\n{tb}")

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

    async def open_editor_and_ask(self):
        template = self._prepare_editor_template()
        loop = asyncio.get_running_loop()
        edited_text = await loop.run_in_executor(
            None, self._open_editor_blocking, template
        )
        if edited_text:
            self.print(f"💬 $ {edited_text}", style="usermsg")
            self.input_window.buffer.history.append_string(edited_text)
            await self.session.ask(edited_text)
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

    def _prepare_editor_template(self) -> str:
        if not len(self.session.last_output):
            return ""
        return (
            "\n\n\n\n\n"
            + "\n".join(f"# {line}" for line in self.session.last_output)
            + "\n\n"
        )

    def handle_ctrl_c(self, event):
        self.session._interrupted = True
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
        self.status_bar.text = f"Status: {status.status_line()}"
        self.status_bar.buffer.cursor_position = 0
        should_animate = status.is_busy()
        if should_animate:
            if self._status_task is None or self._status_task.cancelled():
                self._status_task = asyncio.create_task(
                    self.start_status_animation(status)
                )
        else:
            if self._status_task:
                self._status_task.cancel()

    async def start_status_animation(self, status):
        animation_frames = ["|", "/", "-", "\\"]
        idx = 0
        while True:
            self.status_bar.text = (
                f"Status: {status.status_line()} - {animation_frames[idx]}"
            )
            self.status_bar.buffer.cursor_position = 0
            idx = (idx + 1) % len(animation_frames)
            await asyncio.sleep(0.5)


def main():
    repl = REPLContextManager()
    asyncio.run(repl.run())


if __name__ == "__main__":
    main()
