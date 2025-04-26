# Grep Tool

`grep` searches for specified patterns within files or directories, utilizing the `grep` command functionality.

## Parameters

- `pattern` (string): The pattern to search for. Supports regex.
- `paths` (list of strings): Files or directories in which to conduct the search.
- `ignore_patterns` (optional list of strings): Patterns to exclude from the search.
- `include_pattern` (optional string): Limit search to files matching this pattern.
- `ignore_case` (optional boolean): Perform a case-insensitive search if true.

The tool efficiently searches content, granting the ability to include or exclude files as needed using patterns.
