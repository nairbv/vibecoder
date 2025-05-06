import unittest

from vibecoder.tools.fetch_url import FetchUrlTool


class TestFetchUrlTool(unittest.TestCase):
    def setUp(self):
        self.tool = FetchUrlTool()

    def test_missing_url(self):
        result = self.tool.run({})
        self.assertIn("[Error: Missing 'url' argument.]", result)

    def test_invalid_url(self):
        # This should fail cleanly, not crash
        result = self.tool.run({"url": "http://not-a-real-url-xyz.test/"})
        self.assertIn("[Error", result)

    def test_trafilatura_not_installed(self):
        # Simulate trafilatura not installed
        import sys

        orig = sys.modules.get("trafilatura", None)
        sys.modules["trafilatura"] = None
        result = self.tool.run({"url": "https://example.com"})
        if orig is not None:
            sys.modules["trafilatura"] = orig
        else:
            del sys.modules["trafilatura"]
        self.assertIn("trafilatura package is not installed", result)

    # Note: An actual fetch test is not robust for unit test suites (depends on network), so not included


if __name__ == "__main__":
    unittest.main()
