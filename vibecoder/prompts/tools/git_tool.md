# Git Tool Documentation

The Git Tool enables executing Git read commands such as `status`, `log`, `diff`, `show`, and `grep`. This tool facilitates tracking changes, understanding modifications, and general introspection of the codebase's Git history.

## Parameters

- **command**: The primary Git command to execute (e.g., `status`, `log`, `diff`, `show`, `grep`). This parameter is required.

- **options**: An array of options to provide additional flags or parameters for the Git command (e.g., `['--since=2.weeks']`). This is optional.

- **paths**: An array of file paths or patterns that the command should consider (e.g., `['src/', 'README.md']`). This is optional.

## Usage Examples

1. **Get Status**:
   ```python
   git_tool.run({"command": "status"})
   ```
   This will return the current status of the Git repository.

2. **View Log**:
   ```python
   git_tool.run({"command": "log", "options": ["--oneline", "--since=1.week"]})
   ```
   Displays the commit log in a compact form for the last week.

3. **Inspect Diff**:
   ```python
   git_tool.run({"command": "diff", "paths": ["README.md"]})
   ```
   Shows differences for the `README.md` file.

## Error Handling

The tool returns error messages in case of invalid commands or failures in execution. Make sure to verify command syntax and repository status when errors occur.

## Notes

This tool is designed for read-only operations within Git. It does not support modifications to the repository such as adding or committing changes.
