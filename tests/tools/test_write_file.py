from vibecoder.tools.write_file import WriteFileTool


def test_write_file_success(tmp_path):
    """Test writing to a new file."""

    file_path = tmp_path / "newfile.txt"

    tool = WriteFileTool()
    content = "New content for vibecoder."
    output = tool.run({"path": str(file_path), "content": content})

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
    tool.run({"path": str(file_path), "content": appended_content, "append": True})

    # Verify
    expected_content = initial_content + appended_content
    assert file_path.read_text() == expected_content


def test_write_file_missing_arguments():
    """Test missing arguments returns error."""

    tool = WriteFileTool()
    output = tool.run({"path": "somepath.txt"})  # missing 'content'

    assert "Error" in output
