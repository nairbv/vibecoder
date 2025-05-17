import asyncio
import os
import tempfile
import unittest

from vibecoder.tools.grep import GrepTool


class TestGrepTool(unittest.TestCase):
    def setUp(self):
        self.grep_tool = GrepTool()
        # Create a temporary directory
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        # Clean up the temporary directory
        self.test_dir.cleanup()

    def test_basic_search(self):
        # Create a temporary file with known content
        with open(os.path.join(self.test_dir.name, "test.txt"), "w") as f:
            f.write("this is a test string")
        # Run the async tool
        result = asyncio.run(
            self.grep_tool.run({"pattern": "test", "paths": [self.test_dir.name]})
        )
        self.assertIn("test", result)

    def test_case_insensitive_search(self):
        # Create a temporary file with known content
        with open(os.path.join(self.test_dir.name, "case.txt"), "w") as f:
            f.write("This is a Test string")
        # Run the async tool with ignore_case
        result = asyncio.run(
            self.grep_tool.run(
                {"pattern": "test", "paths": [self.test_dir.name], "ignore_case": True}
            )
        )
        self.assertIn("This is a Test string", result)

    def test_include_pattern(self):
        # Create a matching Python file within the directory
        with open(os.path.join(self.test_dir.name, "script.py"), "w") as f:
            f.write("def func(): pass")
        # Run the async tool with include_pattern
        result = asyncio.run(
            self.grep_tool.run(
                {
                    "pattern": "def ",
                    "paths": [self.test_dir.name],
                    "include_pattern": "*.py",
                }
            )
        )
        self.assertIn("def func(): pass", result)

    def test_exclude_pattern(self):
        # Create a file that should be excluded
        with open(os.path.join(self.test_dir.name, "test_exclude.txt"), "w") as f:
            f.write("import os")
        # And one that should be included
        with open(os.path.join(self.test_dir.name, "include.txt"), "w") as f:
            f.write("import sys")
        # Run grep tool
        # Run the async tool with ignore_patterns
        result = asyncio.run(
            self.grep_tool.run(
                {
                    "pattern": "import",
                    "paths": [self.test_dir.name],
                    "ignore_patterns": ["test_exclude.txt"],
                }
            )
        )
        self.assertNotIn("test_exclude.txt:import os", result)

    def test_empty_paths(self):
        # No paths provided should error
        result = asyncio.run(self.grep_tool.run({"pattern": "test", "paths": []}))
        self.assertEqual(result, "[Error: No valid paths provided!]")


if __name__ == "__main__":
    unittest.main()
