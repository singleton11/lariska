# Agents

## Running and testing

See [README.md](README.md) for instructions on how to install, run, and test the application.

## Testing conventions

Always cover new functionality with integration tests.

When you run pytest (via `uv run pytest`), you'll get coverage report alongside with test report. The coverage of the project after the patch must be not less than the report before. Otherwise build will fail.
