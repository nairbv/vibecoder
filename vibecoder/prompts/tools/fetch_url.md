# `fetch_url` Tool

`fetch_url(url)` - retrieves and extracts meaningful web content from a URL. This tool uses `BeautifulSoup` and `markdownify` to return the main content of the page converted to Markdown format (preserving URLs).

## Parameters

- `url` (string): The URL to fetch and extract content from.

## Description

Given a URL, this tool fetches its HTML content and extracts readable main text, including links. Returns extracted text as markdown, or an error message if the fetching or extraction fails.
