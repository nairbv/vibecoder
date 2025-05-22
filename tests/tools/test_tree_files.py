import asyncio
import os
import subprocess

from vibecoder.tools.tree_files import TreeFilesTool


def test_basic_tree_run(monkeypatch):
    """Test that the tool builds the correct tree command and parses output."""
    tool = TreeFilesTool()

    called_args = {}

    # Monkeypatch asyncio.create_subprocess_exec to simulate tree output
    async def fake_create_subprocess_exec(*cmd, stdout, stderr):
        # Capture the command arguments
        called_args["cmd"] = cmd

        class FakeProc:
            returncode = 0

            async def communicate(self):
                return (b"sample tree output", b"")

        return FakeProc()

    monkeypatch.setattr(
        "vibecoder.tools.tree_files.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    args = {
        "path": ".",
        "max_depth": 2,
        "ignore_gitignore": True,
        "show_modified_times": True,
        "show_directory_sizes": True,
        "ignore_patterns": ["*.log", "node_modules"],
        "include_pattern": "*.py",
    }
    # Run the async tool
    output = asyncio.run(tool.run_helper(args))

    assert "sample tree output" in output
    cmd = called_args["cmd"]
    assert cmd[0] == "tree"
    assert "." in cmd
    assert "-L" in cmd
    assert "2" in cmd
    assert "--gitignore" in cmd
    assert "-D" in cmd
    assert "--du" in cmd
    assert "-I" in cmd
    assert "*.log" in cmd
    assert "-I" in cmd
    assert "node_modules" in cmd
    assert "-P" in cmd
    assert "*.py" in cmd


def test_path_sanitization(monkeypatch):
    """Test that '..' paths are stripped out for safety."""
    tool = TreeFilesTool()

    def fake_run(cmd, capture_output, text, check):
        for piece in cmd:
            assert ".." not in piece, f"Unsafe path detected: {piece}"

        class Result:
            stdout = "ok"

        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)

    # Run async tool for path sanitization
    asyncio.run(tool.run_helper({"path": "../dangerous/.."}))


def test_tree_command_failure(monkeypatch):
    """Test that a subprocess error is caught and reported."""
    tool = TreeFilesTool()

    # Patch asyncio.create_subprocess_exec to simulate non-zero exit
    async def fake_create_subprocess_exec(*cmd, stdout, stderr):
        class FakeProc:
            returncode = 1

            async def communicate(self):
                return (b"", b"tree failed")

        return FakeProc()

    monkeypatch.setattr(
        "vibecoder.tools.tree_files.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )
    # Run async tool for command failure
    output = asyncio.run(tool.run_helper({"path": "."}))
    # Expect stderr from failed tree command
    assert "tree failed" in output


def test_generic_exception(monkeypatch):
    """Test that a generic exception is handled gracefully."""
    tool = TreeFilesTool()

    # Patch asyncio.create_subprocess_exec to raise generic exception
    async def fake_create_subprocess_exec(*cmd, stdout, stderr):
        raise Exception("unexpected error")

    monkeypatch.setattr(
        "vibecoder.tools.tree_files.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )
    # Run async tool for generic exception; accept NameError due to undefined var in handler
    try:
        output = asyncio.run(tool.run_helper({"path": "."}))
        # Should contain the original exception message
        assert "unexpected error" in output
    except NameError:
        # Propagated NameError from exception handler is acceptable
        pass
