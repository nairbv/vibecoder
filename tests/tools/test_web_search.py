import asyncio
import os
import unittest
from unittest.mock import patch

from vibecoder.tools.web_search import SearchTool


class TestWebSearchTool(unittest.TestCase):
    def setUp(self):
        self.tool = SearchTool()
        os.environ["BRAVE_SEARCH_API_KEY"] = "fake-key"

    @patch("requests.get")
    def test_run_successful_search(self, mock_get):
        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "web": {
                        "results": [
                            {
                                "url": "https://abc.com",
                                "title": "ABC",
                                "description": "DescA",
                            },
                            {
                                "url": "https://def.com",
                                "title": "DEF",
                                "description": "DescB",
                            },
                        ]
                    }
                }

        mock_get.return_value = FakeResp()

        # Override fetch_url to use FakeResp
        async def fake_fetch_url(url, headers, params, timeout):
            return FakeResp()

        self.tool.fetch_url = fake_fetch_url
        query = "climate change news"
        args = {"query": query, "count": 2}
        # Run asynchronous tool.run
        out = asyncio.run(self.tool.run(args))
        assert f"## Search results for: {query}" in out
        assert "[ABC](https://abc.com)" in out
        assert "DescA" in out
        assert "[DEF](https://def.com)" in out
        assert "DescB" in out
        assert out.count("- (") == 2

    def test_run_empty_results(self):
        # Simulate empty search results by patching fetch_url
        class DummyResp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"web": {"results": []}}

        # Override async fetch_url to return DummyResp
        async def fake_fetch_url(url, headers, params, timeout):
            return DummyResp()

        self.tool.fetch_url = fake_fetch_url
        # Ensure API key is set for BRAVE
        os.environ["BRAVE_API_KEY"] = "fake-key"
        args = {"query": "somethingnoresults", "count": 3}
        out = asyncio.run(self.tool.run(args))
        assert "No results found" in out

    def test_run_api_key_missing(self):
        if "BRAVE_SEARCH_API_KEY" in os.environ:
            del os.environ["BRAVE_SEARCH_API_KEY"]
        out = asyncio.run(self.tool.run({"query": "x"}))
        assert "API key" in out or "Error" in out

    def test_run_http_error(self):
        # Simulate HTTP error via fetch_url
        class Boom(Exception):
            pass

        async def fake_fetch_url(url, headers, params, timeout):
            raise Boom("BOOM_FAIL")

        self.tool.fetch_url = fake_fetch_url
        os.environ["BRAVE_SEARCH_API_KEY"] = "fake-key"
        out = asyncio.run(self.tool.run({"query": "foo"}))
        # Expect the Boom message in error output
        assert "BOOM_FAIL" in out

    def test_unsupported_engine(self):
        out = asyncio.run(self.tool.run({"query": "x", "engine": "not_valid"}))
        assert "not supported" in out or "Error" in out, out

    def test_do_search_direct(self):
        # test do_search returns result list
        class DummyResp:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "web": {"results": [{"url": "a", "title": "b", "description": "c"}]}
                }

        # Patch fetch_url to return dummy response asynchronously
        async def fake_fetch_url(url, headers, params, timeout):
            return DummyResp()

        self.tool.fetch_url = fake_fetch_url
        # Ensure API key for Brave search
        os.environ["BRAVE_API_KEY"] = "dummy-key"
        out = asyncio.run(self.tool.do_search({"query": "a", "count": 1}))
        assert isinstance(out, list)
        assert out[0]["title"] == "b"


if __name__ == "__main__":
    unittest.main()
