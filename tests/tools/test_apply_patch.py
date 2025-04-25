import pytest
from vibecoder.tools.apply_patch_lib import DiffError
from vibecoder.tools.apply_patch import ApplyPatchTool

def test_apply_patch_success(monkeypatch):
    """Test successful patch application."""

    tool = ApplyPatchTool()

    called = {}

    def fake_process_patch(text, open_fn, write_fn, remove_fn):
        called["patch_text"] = text
        return "Done!"

    monkeypatch.setattr("vibecoder.tools.apply_patch_lib.process_patch", fake_process_patch)

    args = {"input": "*** Begin Patch\n...patch content...\n*** End Patch"}
    output = tool.run(args)

    assert "Done!" in output
    assert "*** Begin Patch" in called["patch_text"]

def test_apply_patch_missing_input():
    """Test missing input argument."""

    tool = ApplyPatchTool()
    output = tool.run({})  # No input provided
    assert "Error" in output
    assert "input" in output

def test_apply_patch_diff_error(monkeypatch):
    """Test handling of a controlled DiffError."""

    tool = ApplyPatchTool()

    def fake_process_patch(text, open_fn, write_fn, remove_fn):
        raise DiffError("Patch failed.")

    monkeypatch.setattr("vibecoder.tools.apply_patch_lib.process_patch", fake_process_patch)

    args = {"input": "*** Begin Patch\n...bad patch...\n*** End Patch"}
    output = tool.run(args)

    assert "Patch application failed" in output

def test_apply_patch_generic_exception(monkeypatch):
    """Test handling of an unexpected exception."""

    tool = ApplyPatchTool()

    def fake_process_patch(text, open_fn, write_fn, remove_fn):
        raise Exception("Something unexpected")

    monkeypatch.setattr("vibecoder.tools.apply_patch_lib.process_patch", fake_process_patch)

    args = {"input": "*** Begin Patch\n...patch content...\n*** End Patch"}
    output = tool.run(args)

    assert "Unexpected error" in output
