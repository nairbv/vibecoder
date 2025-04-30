# Pytest Tool

**Purpose**:  
The Pytest tool runs tests within the project and captures both the detailed output and any error messages. This helps verify whether recent code changes are correct and identify issues when tests fail.

---

**Inputs**:

- `paths` (list of strings, **required**):  
  One or more paths to test files or directories you wish to run with pytest.

- `verbose` (boolean, optional):  
  If `true`, run tests in verbose mode, showing detailed information about each individual test.

- `quiet` (boolean, optional):  
  If `true`, run tests in quiet mode, reducing the amount of output.

- `maxfail` (integer, optional):  
  If provided, stop running after the specified number of test failures.

- `timeout` (integer, optional):
  Timtout in seconds. Defaults to 60. Cannot be set higher than 600.

---

**Outputs**:

- The full stdout and stderr output from running pytest, including:
  - A detailed report of passed, failed, or skipped tests.
  - Stack traces or failure messages if tests fail.
  - The pytest exit code.

The output allows you to debug issues by inspecting test failure details.

---

**Usage Guidelines**:

- Always specify at least one valid test path.
- Use `verbose=true` to get full test details.
- Use `maxfail` when quickly debugging a few failures.
- Avoid passing free-form pytest options; instead, use the explicit fields provided (`verbose`, `quiet`, `maxfail`).

If a test fails, you are expected to carefully read the captured output and identify what went wrong before making further code changes.
