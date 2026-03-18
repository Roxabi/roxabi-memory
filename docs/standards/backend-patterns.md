# Backend Patterns

Conventions and patterns for backend code in roxabi-vault.

## Module Structure

- One class per module: `db.py` has `MemoryDB`, `async_db.py` has `AsyncMemoryDB`
- Shared SQL and helpers go in dedicated modules (`fts.py`, `schema.py`)
- Public API is defined in `__init__.py` via `__all__`
- Use `from __future__ import annotations` in every module for forward references

## Database Access

- Always use context managers (`with` / `async with`) for database connections
- Call `migrate()` on every connect — never require a separate migration step
- Use parameterized queries (`?` placeholders) — never interpolate user input into SQL
- Set `WAL` journal mode and `foreign_keys=ON` on every connection
- Use `row_factory = sqlite3.Row` for dict-like access to query results

## Error Handling

- Raise `RuntimeError` for programmer errors (using DB before connecting)
- Let `sqlite3` exceptions propagate for database errors
- In the CLI: catch errors, print to stderr, exit with code 1
- No custom exception hierarchy

## Naming Conventions

- Snake case for all Python identifiers
- Module names match the primary class: `db.py` → `MemoryDB`
- Test files mirror source files: `db.py` → `test_db.py`
- Private methods prefixed with `_`: `_conn_or_raise()`, `_row()`, `_safe_query()`

## SQL Conventions

- Use uppercase for SQL keywords: `SELECT`, `INSERT`, `WHERE`
- Use `?` for parameters, never f-strings or string formatting
- Multi-line SQL as triple-quoted strings
- FTS queries are sanitized through `_safe_query()` before reaching `MATCH`

## Dependencies

- Core: only `aiosqlite` (which brings in `sqlite3`)
- CLI: `typer` + `rich` (optional extra `[cli]`)
- Embeddings: `fastembed` + `sqlite-vec` (optional extra `[embeddings]`, not yet implemented)
- No ORM — raw SQL only

## AI Quick Reference

<!-- Compressed imperative rules for dev-core agents. Keep under 10 lines. -->

- ALWAYS use parameterized queries with `?` — never interpolate into SQL
- ALWAYS use context managers for DB connections
- ALWAYS call `migrate()` inside `connect()` — never separately
- ALWAYS sanitize FTS queries through `_safe_query()`
- NEVER import `sqlite3` directly in consumer code — use `MemoryDB` or `AsyncMemoryDB`
- NEVER add ORM dependencies — this project uses raw SQL by design
- RETURN `MemoryEntry` dataclass from sync API, `dict` from async API
