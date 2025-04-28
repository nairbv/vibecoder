from vibecoder.tools.read_file import ReadFileTool


def test_read_file_success(tmp_path):
    """Test reading an existing file."""

    # Create a temporary file
    file_path = tmp_path / "test.txt"
    file_path.write_text(
        """Hello, vibecoder!
Welcome to the test file.
This is line three."""
    )

    tool = ReadFileTool()
    output = tool.run({"path": str(file_path)})

    assert "Hello, vibecoder!" in output


def test_read_file_with_start(tmp_path):
    """Test reading file beginning from a specific line number."""

    file_path = tmp_path / "test.txt"
    file_path.write_text(
        """Hello, vibecoder!
Welcome to the test file.
This is line three."""
    )

    tool = ReadFileTool()
    output = tool.run({"path": str(file_path), "start": 1})

    assert "Welcome to the test file." in output
    assert "Hello, vibecoder!" not in output


def test_read_file_with_start_and_end(tmp_path):
    """Test reading file with specified start and end line numbers."""

    file_path = tmp_path / "test.txt"
    file_path.write_text(
        """Hello, vibecoder!
Welcome to the test file.
This is line three."""
    )

    tool = ReadFileTool()
    output = tool.run({"path": str(file_path), "start": 1, "end": 2})

    assert "Welcome to the test file." in output
    assert "This is line three." not in output


def test_read_file_missing_file():
    """Test reading a non-existent file returns error."""

    tool = ReadFileTool()
    output = tool.run({"path": "nonexistent_file.txt"})

    assert "Error" in output
