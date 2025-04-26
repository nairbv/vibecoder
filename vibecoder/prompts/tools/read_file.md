### Tool: read_file

Use this tool to examine code or documentation in the project.

**Arguments:**
- `path`: a relative path to a file within the project.
- `start`: (optional) an integer specifying the starting line number for reading the file (inclusive).
- `end`: (optional) an integer specifying the ending line number for reading the file (exclusive).

**Returns:**
The full contents of the file or a portion of it as defined by the `start` and `end` line numbers.

**Example use:**
> Call `read_file("vibecoder/main.py", start=0, end=10)` to inspect the first 10 lines of the entrypoint logic.
