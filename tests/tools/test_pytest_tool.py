import asyncio
import os
import tempfile
import time
import warnings

import pytest

from vibecoder.tools.pytest_tool import PytestTool


def test_pytest_tool_timeout():
    """Test that the pytest tool times out and kills tests that hang."""
    tool = PytestTool()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file_path = os.path.join(tmpdir, "test_hang.py")
        with open(test_file_path, "w") as f:
            f.write(
                """
import time
def test_hang():
    time.sleep(30)  # Sleep a long time to simulate hang
"""
            )

        args = {
            "paths": [test_file_path],
            "verbose": True,
            "timeout": 1,  # 1 second timeout
        }

        previous_dir = tempfile.gettempdir()

        # Change cwd to temp dir for isolated run
        try:
            os.chdir(tmpdir)
            # Run the async tool with timeout
            output = asyncio.run(tool.run(args))
        finally:
            os.chdir(previous_dir)

        assert (
            "timeout" in output.lower() or "killed" in output.lower()
        ), f"Unexpected output: {output}"


def test_pytest_tool_basic_run():
    """Test running PytestTool on a small passing test file."""
    tool = PytestTool()


def test_pytest_tool_basic_run():
    """Test running PytestTool on a small passing test file."""
    tool = PytestTool()

    # Create a temporary directory and a dummy test file
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file_path = os.path.join(tmpdir, "test_dummy.py")
        with open(test_file_path, "w") as f:
            f.write(
                """
def test_dummy():
    assert 1 + 1 == 2
"""
            )

        args = {
            "paths": [test_file_path],
            "verbose": True,
        }

        # Use a warnings filter context to suppress deprecation warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)

            # Use the temporary directory as a fallback
            previous_dir = tempfile.gettempdir()

            # Change the current directory for running the tool
            try:
                os.chdir(tmpdir)
                # Run the async tool for basic run
                output = asyncio.run(tool.run(args))
            finally:
                os.chdir(previous_dir)

        # Basic checks
        assert "Exit code:" in output
        assert "STDOUT:" in output
        assert "test_dummy" in output
        assert "1 passed" in output


def test_pytest_tool_failure_capture():
    """Test that failing tests produce useful output."""
    tool = PytestTool()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file_path = os.path.join(tmpdir, "test_fail.py")
        with open(test_file_path, "w") as f:
            f.write(
                """
def test_fail():
    assert 1 == 2
"""
            )

        args = {
            "paths": [test_file_path],
            "verbose": True,
        }

        # Suppress deprecation warnings and manage directory context
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)

            # Use the temporary directory as a fallback
            previous_dir = tempfile.gettempdir()

        # Change the current directory for running the tool
        try:
            os.chdir(tmpdir)
            # Run the async tool for failure capture
            output = asyncio.run(tool.run(args))
        finally:
            os.chdir(previous_dir)

        assert "Exit code:" in output
        assert "STDOUT:" in output
        assert "test_fail" in output
        assert "assert 1 == 2" in output or "AssertionError" in output
        assert "failed" in output.lower()
