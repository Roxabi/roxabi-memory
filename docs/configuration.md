# Configuration

How roxabi-vault is configured — environment variables, CLI options, and Python API defaults.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `VAULT_DB` | Yes (if not using `--db`) | — | Path to the SQLite database file. Used by the `vault` CLI. |

No other environment variables are used. The library itself takes the database path as a constructor argument.

## CLI Options

Global options (set before any subcommand):

| Option | Env fallback | Description |
|---|---|---|
| `--db PATH` | `VAULT_DB` | Path to the SQLite database file. Required. |
| `--json` | — | Output results as JSON instead of Rich tables. |

Example:

```bash
# Via flag
vault --db ~/.roxabi/memory.db list

# Via environment variable
export VAULT_DB=~/.roxabi/memory.db
vault list
```

## Python API Defaults

When using `MemoryDB` or `AsyncMemoryDB` directly:

| Parameter | Default | Description |
|---|---|---|
| `path` | (required) | Path to SQLite file, or `":memory:"` for in-memory databases |
| `namespace` | `"vault"` | Default namespace for new entries |
| `category` | `"general"` | Default category for new entries |
| `type` | `"note"` | Default entry type |
| `metadata` | `"{}"` | Default metadata (empty JSON object as string) |
| `limit` | `20` (search) / `50` (list) | Default result limits |

## SQLite Pragmas

Applied automatically on every connection:

| Pragma | Value | Why |
|---|---|---|
| `journal_mode` | `WAL` | Write-Ahead Logging for concurrent read access |
| `foreign_keys` | `ON` | Enforce foreign key constraints (future-proofing) |

## Database Location

The library does not enforce a specific database location. Common conventions:

- **CLI users**: `~/.roxabi/memory.db` (set via `VAULT_DB`)
- **Tests**: `":memory:"` (in-memory, no file created)
- **Agents**: Path configured by the agent runtime

## Optional Dependencies

Installed via pip extras:

```bash
# CLI support (typer + rich)
pip install roxabi-vault[cli]

# Embeddings support (not yet implemented)
pip install roxabi-vault[embeddings]
```
