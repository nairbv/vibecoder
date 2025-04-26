import os
import pytest
import tempfile
from vibecoder.tools.move import MoveTool


def test_move_tool_rename_file():
    tool = MoveTool()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        # Setup: Create a dummy file
        with open("old_name.txt", "w") as f:
            f.write("Test content")
        
        # Execute tool
        result = tool.run({"origin": "old_name.txt", "destination": "new_name.txt"})

        # Verify
        assert result == "Successfully moved from old_name.txt to new_name.txt."
        assert not os.path.exists("old_name.txt")
        assert os.path.exists("new_name.txt")


def test_move_tool_invalid_path():
    tool = MoveTool()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        # Execute tool with invalid path
        result = tool.run({"origin": "/outside.txt", "destination": "new_name.txt"})

        # Verify
        assert "Paths must be relative and confined to the working directory." in result

    
    
def test_move_tool_file_not_found():
    tool = MoveTool()

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        # Execute tool with non-existing file
        result = tool.run({"origin": "non_existent.txt", "destination": "new_name.txt"})

        # Verify
        assert "The file or directory 'non_existent.txt' was not found." in result
