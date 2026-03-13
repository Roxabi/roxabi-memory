# Testing Standards

Testing conventions and requirements for roxabi-vault.

## Test Structure

Tests live in the `tests/` directory and mirror the source layout:

| Source | Test file |
|---|---|
| `db.py` | `test_db.py`, `test_db_methods.py` |
| `async_db.py` | `test_async_db.py` |
| `schema.py` | `test_schema.py` |
| `namespace.py` | `test_namespace.py` |
| `cli.py` | `test_cli.py` |

## Running Tests

```bash
# Run all tests
uv run pytest

# Run a specific file
uv run pytest tests/test_db.py

# Run with verbose output
uv run pytest -v
```

## Test Patterns

### In-Memory Databases

Always use `":memory:"` for test databases — no file I/O, no cleanup needed:

```python
def test_example():
    with MemoryDB(":memory:") as db:
        entry = db.save_entry("test content")
        assert entry.id == 1
```

### Async Tests

Async tests are configured with `asyncio_mode = "auto"` in `pyproject.toml`. Just use `async def`:

```python
async def test_async_example():
    async with AsyncMemoryDB(":memory:") as db:
        entry_id = await db.save_entry("test content")
        assert entry_id == 1
```

### CLI Tests

Use Typer's `CliRunner` for CLI tests. Set `VAULT_DB` or pass `--db` with a temp file:

```python
from typer.testing import CliRunner
from roxabi_vault.cli import app

runner = CliRunner()

def test_cli_list(tmp_path):
    db_path = str(tmp_path / "test.db")
    result = runner.invoke(app, ["--db", db_path, "list"])
    assert result.exit_code == 0
```

### Fixtures

- Use `tmp_path` (pytest built-in) for tests that need a real file
- Use `":memory:"` for everything else
- No shared fixtures across test files — each test is self-contained

## Conventions

- Test function names: `test_<what>_<scenario>` (e.g., `test_save_entry_default_title`)
- One assert per logical behavior — multiple asserts are fine if testing one operation
- No mocking of the database — use real in-memory SQLite
- Tests must be independent — no ordering dependencies between tests

## AI Quick Reference

<!-- Compressed imperative rules for dev-core agents. Keep under 10 lines. -->

- ALWAYS use `":memory:"` databases in tests — never create files unless testing file behavior
- ALWAYS use context managers for DB setup/teardown
- NEVER mock SQLite — use real in-memory databases
- NEVER share state between tests
- USE `async def` for async tests — `asyncio_mode = "auto"` handles the rest
- USE `CliRunner` for CLI tests, not subprocess calls
