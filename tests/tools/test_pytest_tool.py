import os
import tempfile
import warnings
from vibecoder.tools.pytest_tool import PytestTool


def test_pytest_tool_basic_run():
    """Test running PytestTool on a small passing test file."""
    tool = PytestTool()

    # Create a temporary directory and a dummy test file
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file_path = os.path.join(tmpdir, "test_dummy.py")
        with open(test_file_path, "w") as f:
            f.write("""
def test_dummy():
    assert 1 + 1 == 2
""")

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
                output = tool.run(args)
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
            f.write("""
def test_fail():
    assert 1 == 2
""")

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
                output = tool.run(args)
            finally:
                os.chdir(previous_dir)

        assert "Exit code:" in output
        assert "STDOUT:" in output
        assert "test_fail" in output
        assert "assert 1 == 2" in output or "AssertionError" in output
        assert "failed" in output.lower()
