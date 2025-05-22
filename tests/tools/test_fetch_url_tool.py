import asyncio
import os
import unittest

from vibecoder.tools.fetch_url import FetchUrlTool


class TestFetchUrlTool(unittest.TestCase):
    def setUp(self):
        self.tool = FetchUrlTool()

    def test_missing_url(self):
        # No URL provided should return missing argument error
        result = asyncio.run(self.tool.run_helper({}))
        self.assertIn("[Error: Missing 'url' argument.]", result)

    def test_invalid_url(self):
        # This should fail cleanly, not crash
        result = asyncio.run(
            self.tool.run_helper({"url": "http://not-a-real-url-xyz.test/"})
        )
        self.assertIn("[Error", result)

    def test_fetch_markdown_output(self):
        """
        Test that fetching a valid URL returns markdown content including known text.
        """
        # Fetch example.com and verify markdown output contains expected title
        result = asyncio.run(self.tool.run_helper({"url": "https://example.com"}))
        self.assertIn("Example Domain", result)

    # Note: An actual fetch test is not robust for unit test suites (depends on network), so not included

    def test_html_to_markdown_basic(self):
        """
        Test html_to_markdown utility directly with static HTML.
        """
        from vibecoder.tools.fetch_url import html_to_markdown

        html = "<html><body>" "<p>Hello <strong>World</strong>!</p>" "</body></html>"
        md = html_to_markdown(html)
        # Basic paragraph and strong should be converted
        self.assertIn("Hello **World**!", md)

    def test_html_to_markdown_strip_tags(self):
        from vibecoder.tools.fetch_url import html_to_markdown

        html = (
            "<html><body>"
            "<script>ignore()</script>"
            "<p>Keep this text.</p>"
            "<span>Hi</span>"  # should be removed by min_words default
            "</body></html>"
        )
        md = html_to_markdown(html, min_words=2)
        self.assertIn("Keep this text.", md)
        self.assertNotIn("Hi", md)


if __name__ == "__main__":
    unittest.main()
