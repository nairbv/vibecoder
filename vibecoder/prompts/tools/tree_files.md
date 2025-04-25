### Tool: tree_files

Lists project files and directories using the `tree` command. Supports various options for customized listing.

**Arguments:**
- `path` (optional): Root directory to list (default is '.'). Only allowed to access current project and subdirectories.
- `max_depth` (optional): Maximum directory depth to recurse into.
- `ignore_gitignore` (optional): If true, ignores files matching .gitignore patterns.
- `ignore_patterns` (optional): A list of filename patterns to exclude (e.g., `["*.log", "node_modules"]`).
- `include_pattern` (optional): Only list files matching a specific pattern (e.g., `"*.py"`).
- `show_modified_times` (optional): Show last modification dates next to files.
- `show_directory_sizes` (optional): Show total size of each directory including its contents.

**Behavior:**
- Files and directories are shown in a tree-like, human-readable format.
- Hidden files (those starting with `.`) are shown if included explicitly.
- Cannot navigate outside the current project directory (no `..` allowed).
