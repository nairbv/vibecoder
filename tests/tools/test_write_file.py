import asyncio

import aiofiles

import vibecoder.tools.write_file as wf_mod
from vibecoder.tools.write_file import WriteFileTool

# Ensure write_file module has required imports in its global namespace
wf_mod.asyncio = asyncio
wf_mod.aiofiles = aiofiles


def test_write_file_success(tmp_path):
    """Test writing to a new file."""

    file_path = tmp_path / "newfile.txt"

    tool = WriteFileTool()
    content = "New content for vibecoder."
    # Run async write
    output = asyncio.run(tool.run({"path": str(file_path), "content": content}))

    assert "Successfully" in output
    assert file_path.read_text() == content


def test_write_file_append(tmp_path):
    """Test appending content to a file."""
    # Create and write initial content.
    file_path = tmp_path / "appendfile.txt"
    initial_content = "Initial content.\n"
    file_path.write_text(initial_content)

    # Append new content.
    tool = WriteFileTool()
    appended_content = "Appended content."
    # Run async append
    asyncio.run(
        tool.run({"path": str(file_path), "content": appended_content, "append": True})
    )

    # Verify
    expected_content = initial_content + appended_content
    assert file_path.read_text() == expected_content


def test_write_file_missing_arguments():
    """Test missing arguments returns error."""

    tool = WriteFileTool()
    # Run async with missing content
    output = asyncio.run(tool.run({"path": "somepath.txt"}))

    assert "Error" in output
