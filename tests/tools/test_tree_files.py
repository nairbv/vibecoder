import subprocess
from vibecoder.tools.tree_files import TreeFilesTool

def test_basic_tree_run(monkeypatch):
    """Test that the tool builds the correct tree command and parses output."""
    tool = TreeFilesTool()

    called_args = {}

    def fake_run(cmd, capture_output, text, check):
        called_args["cmd"] = cmd
        class Result:
            stdout = "sample tree output"
        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)

    args = {
        "path": ".",
        "max_depth": 2,
        "ignore_gitignore": True,
        "show_modified_times": True,
        "show_directory_sizes": True,
        "ignore_patterns": ["*.log", "node_modules"],
        "include_pattern": "*.py"
    }
    output = tool.run(args)

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

    tool.run({"path": "../dangerous/.."})

def test_tree_command_failure(monkeypatch):
    """Test that a subprocess error is caught and reported."""
    tool = TreeFilesTool()

    def fake_run(cmd, capture_output, text, check):
        raise subprocess.CalledProcessError(
            returncode=1, cmd=cmd, stderr="tree failed"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    output = tool.run({"path": "."})
    assert "tree failed" in output

def test_generic_exception(monkeypatch):
    """Test that a generic exception is handled gracefully."""
    tool = TreeFilesTool()

    def fake_run(cmd, capture_output, text, check):
        raise Exception("unexpected error")

    monkeypatch.setattr(subprocess, "run", fake_run)

    output = tool.run({"path": "."})
    assert "unexpected error" in output

