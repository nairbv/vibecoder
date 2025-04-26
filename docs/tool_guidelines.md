# Adding new tools to Vibe Coder

## Files

Each tool has:

* A unit test in tests/tools/test_`tool_name`_tool.py
* A file describing its usage in vibecoder/prompts/tools/`tool_name`.md
* A subclass of Tool, called `tool_name`Tool(Tool) in vibecoder/tools/`tool_name`.py. This file must read the .md file.
* If the intent is for use by a software developing agent (most tools), an entry in vibecoder/agents/swe.py

## Guidelines

When adding a tool, it should follow the pattern of other implemented tools. Read examples from other tools carefully.

Generally speaking, when adding a tool, don't just dump raw text into a shell command. Tools should be strictly typed. For example:

    If we're calling a command like git, it will have an argument like "command" (one of diff, log, show, etc).

    A flag on the command line can be an optional boolean argument.

    A parameter like -A in `grep -A 3` can be an optional argument, maybe called "after", with type int.

    Any raw text should be sanitized and quoted.

    Paths should not have leading '/' and should not have `..`. The agent is only permitted to view the working directory.

Make sure relevant output is captured and returned to the agent.

## Global Tool List

All tools should be defined in the `vibecoder/tools` directory. They are automatically collected using the `get_all_tools` function from the `__init__.py` module in the same directory. This ensures any new tool will automatically be included in the validation tests. Therefore, ensure all new tools subclass the `Tool` base class and implement the necessary methods. This ensures seamless integration into our testing framework.