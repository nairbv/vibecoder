# Move Tool

## Description

The Move Tool (`move_tool`) allows you to move or rename files and directories within the project. This tool ensures that the operation is safe by preventing paths with leading slashes or '..', restricting access to the current working directory.

## Usage

- **Origin** (string): The path of the file or directory to be moved. Must be relative and within the working directory.
- **Destination** (string): The target path for the file or directory. Must also be relative and within the working directory.

The tool performs a simple rename operation, which can be used to move files across directories or simply rename them within the current directory structure.

### Example

To rename a file `old_name.txt` to `new_name.txt`:

```python
move_tool.run({"origin": "old_name.txt", "destination": "new_name.txt"})
```

To move a file to a different directory:

```python
move_tool.run({"origin": "folder1/old_name.txt", "destination": "folder2/new_name.txt"})
```

## Error Handling

- Ensures both paths are valid and within the working directory.
- Provides informative error messages if the operation cannot be completed.
