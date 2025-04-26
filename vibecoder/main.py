import os
import click
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout

from vibecoder.agents.swe import build_swe_agent

HISTORY_FILE = os.path.expanduser("~/.vibecoder_history")


def load_env():
    if os.path.exists(".env"):
        load_dotenv()
    else:
        print("Warning: .env file not found, OPENAI_API_KEY may not be set.")

def is_command(line: str):
    return line.startswith("/")


def open_editor_with_template(template_text=""):
    """Opens system $EDITOR with optional template text."""
    edited_text = click.edit(text=template_text)
    if edited_text is not None:
        return edited_text.strip()
    return ""

def do_ask(line, agent):
    for output in agent.ask(line):
        print(f"🤖 SWE: {output}")


def handle_line(line, agent):
    if is_command(line):
        command = line[1:].strip()
        if command in {"quit", "exit"}:
            print("👋 Exiting vibecoder.")
            exit(0)
        elif command == "edit":
            command = open_editor_with_template()
            do_ask(command, agent)
        else:
            print(f"⚠️ Unknown command: /{command}")
    else:
        do_ask(line, agent)

def main():
    load_env()

    agent = build_swe_agent()

    history_path = os.path.expanduser("~/.vibecoder_history")
    session = PromptSession(history=FileHistory(history_path))

    print("🤖 vibecoder (type /quit to exit)\n")

    with patch_stdout():
        while True:
            try:
                line = session.prompt("💬 $ ")
                if not line.strip():
                    continue

                handle_line(line, agent)

            except KeyboardInterrupt:
                print("\n(Use /quit to exit)")
            except EOFError:
                break

if __name__ == "__main__":
    main()

