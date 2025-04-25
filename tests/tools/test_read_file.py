from vibecoder.tools.read_file import ReadFileTool

def test_read_file_success(tmp_path):
    """Test reading an existing file."""

    # Create a temporary file
    file_path = tmp_path / "test.txt"
    file_path.write_text("Hello, vibecoder!")

    tool = ReadFileTool()
    output = tool.run({"path": str(file_path)})

    assert "Hello, vibecoder!" in output

def test_read_file_missing_file():
    """Test reading a non-existent file returns error."""

    tool = ReadFileTool()
    output = tool.run({"path": "nonexistent_file.txt"})

    assert "Error" in output
