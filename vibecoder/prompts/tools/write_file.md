### Tool: write_file

Writes new content to a file. By default, overwrites the existing content unless append is specified.

**Arguments:**
- `path`: The relative path where the file should be written.
- `content`: The complete contents to write into the file.
- `append`: (optional) If true, append the content instead of overwriting. Defaults to false.

**Returns:**
Success confirmation message or an error if unable to write.
