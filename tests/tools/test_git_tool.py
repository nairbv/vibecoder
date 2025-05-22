import asyncio

import pytest

from vibecoder.tools.git_tool import GitTool

git_tool = GitTool()


def test_git_status():
    args = {"command": "status"}
    # Run the async tool
    output = asyncio.run(git_tool.run_helper(args))
    assert (
        "On branch" in output or "Not a git repository" in output
    ), "Unexpected output for 'git status'."


def test_git_invalid_command():
    # For now, we don't allow 'write' commands
    args = {"command": "init"}
    # Run the async tool
    output = asyncio.run(git_tool.run_helper(args))
    assert "Error:" in output, "Expected an error message for an invalid git command."
