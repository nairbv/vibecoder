 # VibeCoder: Autonomous Code Agent

## Overview
VibeCoder is an autonomous coding agent designed to streamline software engineering tasks. It operates as a command-line REPL (Read-Eval-Print Loop) that interacts with users in real-time to analyze tasks, plan solutions, write code, test, and iteratively improve projects.

## Installation

VibeCoder requires Python 3.8 or newer. To set up the environment, follow these steps:

```bash
# Clone the repository
git clone https://github.com/yourusername/vibecoder.git
cd vibecoder

# Install with dependencies
pip install .

```

## Usage

Once installed, you can start the REPL interface:

```bash
python -m vibecoder.main
```
Upon starting, you'll find VibeCoder responsive to typed commands and prompts. Type `/help` within the REPL for a list of available commands.

## Extending VibeCoder

You can add new tools to enhance the agent's capabilities. Each tool consists of implementing a new subclass of the `Tool` base class located in `vibecoder/tools`, alongside its usage documentation and test cases:

- Create a subclass `NewTool(Tool)` in `vibecoder/tools/new_tool.py`.
- Add a usage description in `vibecoder/prompts/tools/new_tool.md`.
- Write unit tests in `tests/tools/test_new_tool.py`.

For more details, see the documentation in the `docs/` directory.

