# Web Search Tool

Searches the internet using the specified search engine API (currently only Brave is supported) and returns a list of relevant web search results (URL, title, and snippet/summary for each result). This tool does NOT fetch the contents of the result URLs — only top-level search results are provided.

## Parameters
- `query` (string): The search query to perform.
- `engine` (string, optional): The search engine to use. Currently, only `brave` is supported. Default is `brave`.
- `count` (integer, optional): The number of results to return (default 5, max 20).

## Output
A list of results. Each result contains:

- `rank` (integer, starting at 1)
- `url` (result URL)
- `title` (result title text)
- `summary` (short snippet, may be empty)

This tool is for quick review of what information is available for a given topic or question on the web.
