import os
import click
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout

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
        self.session = PromptSession(history=FileHistory(HISTORY_FILE))

    def run(self):
        print("🤖 vibecoder (type /quit to exit)\n")

        with patch_stdout():
            while True:
                try:
                    line = self.session.prompt("💬 $ ")
                    if not line.strip():
                        continue
                    self.handle_line(line)

                except KeyboardInterrupt:
                    print("\n(Use /quit to exit)")
                except EOFError:
                    break

    def handle_line(self, line: str):
        if line.startswith("/"):
            self.handle_command(line[1:].strip())
        else:
            self.ask(line)

    def handle_command(self, command: str):
        if command in {"quit", "exit"}:
            print("👋 Exiting vibecoder.")
            exit(0)
        elif command == "edit":
            self.open_editor_and_ask()
        else:
            print(f"⚠️ Unknown command: /{command}")

    def ask(self, line: str):
        outputs = []
        for output in self.agent.ask(line):
            print(f"🤖 SWE: {output}")
            outputs.append(output)
        self.last_output = "\n".join(outputs)

    def open_editor_and_ask(self):
        template = self._prepare_editor_template()
        edited_text = self._open_editor(template)
        if edited_text:
            print(edited_text)
            self.ask(edited_text)

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


def main():
    repl = REPLContextManager()
    repl.run()


if __name__ == "__main__":
    main()
