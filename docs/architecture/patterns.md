# Patterns

Recurring patterns and conventions used in roxabi-vault.

## Context Manager Protocol

Both database classes implement context managers for safe connection lifecycle:

```python
# Sync
with MemoryDB("memory.db") as db:
    db.save_entry("content")

# Async
async with AsyncMemoryDB("memory.db") as db:
    await db.save_entry("content")
```

`connect()` is called on enter, `close()` on exit. Never use the DB without a context manager or explicit `connect()` / `close()` calls.

## Migrate-on-Connect

Schema migration runs automatically on every `connect()`. The `migrate()` function is idempotent:

1. Runs `CREATE TABLE IF NOT EXISTS` / `CREATE TRIGGER IF NOT EXISTS` (v1 DDL)
2. Checks `PRAGMA user_version` for the current schema version
3. Applies any outstanding `ALTER TABLE` statements from the `MIGRATIONS` dict
4. Bumps `user_version` after each migration step

This means consumers never need to run migrations manually.

## Namespace Scoping

Entries are isolated by namespace. All search queries include `vault` entries alongside the requested namespace:

```sql
WHERE (e.namespace = ? OR e.namespace = 'vault')
```

This lets shared/global entries live in `vault` while agent-specific data stays isolated.

## FTS Query Sanitization

User search queries are wrapped in double quotes and stripped of FTS5 special characters (`*`, `^`) before being passed to `MATCH`. This prevents query injection and ensures phrase matching:

```python
safe_q = '"' + query.replace('"', '""').replace("*", "").replace("^", "") + '"'
```

## Dataclass for Sync, Dict for Async

- `MemoryDB` (sync) returns `MemoryEntry` dataclass instances
- `AsyncMemoryDB` (async) returns plain `dict` objects

This is intentional: the async API is designed for lightweight agent use where dicts are easier to serialize. The sync API is used in the CLI where typed access is more convenient.

## CLI State Pattern

The CLI uses a Typer callback to capture global options (`--db`, `--json`) into a module-level `_State` object. All subcommands read from this shared state:

```python
@app.callback()
def main(db: str, as_json: bool) -> None:
    state.db_path = Path(db)
    state.as_json = as_json
```

## Error Handling

- Database classes raise `RuntimeError` if used before `connect()`
- The CLI prints errors to stderr via a separate `Console(stderr=True)` and exits with code 1
- No custom exception hierarchy — the library is simple enough to use stdlib exceptions
