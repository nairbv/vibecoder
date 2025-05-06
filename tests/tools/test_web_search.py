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
        query = "climate change news"
        args = {"query": query, "count": 2}
        out = self.tool.run(args)
        assert f"## Search results for: {query}" in out
        assert "[ABC](https://abc.com)" in out
        assert "DescA" in out
        assert "[DEF](https://def.com)" in out
        assert "DescB" in out
        assert out.count("- (") == 2

    @patch("requests.get")
    def test_run_empty_results(self, mock_get):
        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"web": {"results": []}}

        mock_get.return_value = FakeResp()
        args = {"query": "somethingnoresults", "count": 3}
        out = self.tool.run(args)
        assert "No results found" in out

    def test_run_api_key_missing(self):
        if "BRAVE_SEARCH_API_KEY" in os.environ:
            del os.environ["BRAVE_SEARCH_API_KEY"]
        out = self.tool.run({"query": "x"})
        assert "API key" in out or "Error" in out

    @patch("requests.get")
    def test_run_http_error(self, mock_get):
        class Boom(Exception):
            pass

        def fail(*a, **kwa):
            raise Boom("BOOM_FAIL")

        mock_get.side_effect = fail
        os.environ["BRAVE_SEARCH_API_KEY"] = "fake-key"
        out = self.tool.run({"query": "foo"})
        assert "BOOM_FAIL" in out

    def test_unsupported_engine(self):
        out = self.tool.run({"query": "x", "engine": "not_valid"})
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

        with patch("requests.get", return_value=DummyResp()):
            os.environ["BRAVE_SEARCH_API_KEY"] = "z"
            out = self.tool.do_search({"query": "a", "count": 1})
            assert isinstance(out, list)
            assert out[0]["title"] == "b"


if __name__ == "__main__":
    unittest.main()
