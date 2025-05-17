import asyncio
import os
import unittest

from vibecoder.tools.fetch_url import FetchUrlTool


class TestFetchUrlTool(unittest.TestCase):
    def setUp(self):
        self.tool = FetchUrlTool()

    def test_missing_url(self):
        # No URL provided should return missing argument error
        result = asyncio.run(self.tool.run({}))
        self.assertIn("[Error: Missing 'url' argument.]", result)

    def test_invalid_url(self):
        # This should fail cleanly, not crash
        result = asyncio.run(self.tool.run({"url": "http://not-a-real-url-xyz.test/"}))
        self.assertIn("[Error", result)

    def test_fetch_markdown_output(self):
        """
        Test that fetching a valid URL returns markdown content including known text.
        """
        # Fetch example.com and verify markdown output contains expected title
        result = asyncio.run(self.tool.run({"url": "https://example.com"}))
        self.assertIn("Example Domain", result)

    # Note: An actual fetch test is not robust for unit test suites (depends on network), so not included


if __name__ == "__main__":
    unittest.main()
