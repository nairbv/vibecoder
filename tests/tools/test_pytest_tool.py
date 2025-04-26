import os
import tempfile
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

        output = tool.run(args)

        # Basic checks
        assert "Exit code:" in output
        assert "STDOUT:" in output
        assert "test_dummy" in output
        assert "1 passed" in output
        assert "stderr" not in output.lower()  # no stderr expected

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

        output = tool.run(args)

        assert "Exit code:" in output
        assert "STDOUT:" in output
        assert "test_fail" in output
        assert "assert 1 == 2" in output or "AssertionError" in output
        assert "failed" in output.lower()

