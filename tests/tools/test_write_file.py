from vibecoder.tools.write_file import WriteFileTool

def test_write_file_success(tmp_path):
    """Test writing to a new file."""

    file_path = tmp_path / "newfile.txt"

    tool = WriteFileTool()
    content = "New content for vibecoder."
    output = tool.run({"path": str(file_path), "content": content})

    assert "Successfully" in output
    assert file_path.read_text() == content

def test_write_file_missing_arguments():
    """Test missing arguments returns error."""

    tool = WriteFileTool()
    output = tool.run({"path": "somepath.txt"})  # missing 'content'

    assert "Error" in output
