import pytest
from vibecoder.tools.git_tool import GitTool


git_tool = GitTool()


def test_git_status():
    args = {"command": "status"}
    output = git_tool.run(args)
    assert "On branch" in output or "Not a git repository" in output, "Unexpected output for 'git status'."

def test_git_invalid_command():
    args = {"command": "nonexistent_command"}
    output = git_tool.run(args)
    assert "Error:" in output, "Expected an error message for an invalid git command."
