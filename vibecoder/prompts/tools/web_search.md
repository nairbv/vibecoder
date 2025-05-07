# Web Search Tool `web_search`

`web_search(query, count)`  - searches the internet using the Brave search engine API, and returns a list of relevant web search results (URL, title, and snippet/summary for each result). This tool does NOT fetch the contents of the result URLs, but you may have other tools that can do so.

## Parameters
- `query` (string): The search query to perform.
- `count` (integer, optional): The number of results to return (default 5, max 20).

## Output
A list of results. Each result contains:

- `rank` (integer, starting at 1)
- `url` (result URL)
- `title` (result title text)
- `summary` (short snippet, may be empty)

This tool is for quick review of what information is available for a given topic or question on the web, as well as a source of url's from which to fetch more information.
