---
name: vault-init
description: 'Initialize the Roxabi vault — create ~/.roxabi-vault/ with SQLite+FTS5 database, subdirectories, and WAL mode. Triggers: "vault-init" | "init vault" | "setup vault" | "create vault" | "initialize vault".'
version: 0.2.0
allowed-tools: Bash, Read
---

# Vault Init

First-time setup for the Roxabi vault. Creates the vault home directory, subdirectories, and initializes the SQLite+FTS5 database.

All operations go through the `rmem` CLI (installed via `roxabi-memory[cli]`).

## Phase 1 — Check Existing

```bash
rmem --json stats 2>&1 || echo "VAULT_NEW"
```

If vault already exists, report current state and stop. Do not reinitialize.

## Phase 2 — Initialize

```bash
rmem init
```

This creates:
- `~/.roxabi-vault/` with 700 permissions (or `$ROXABI_VAULT_HOME`)
- Subdirectories: `config/`, `content/`, `ideas/`, `learnings/`, `backup/`
- `vault.db` with schema v2, FTS5 index, and WAL mode

## Phase 3 — Verify

```bash
rmem --json stats
```

Confirm the vault is healthy and report:

```
Vault Initialized
  Location:    ~/.roxabi-vault/
  Database:    vault.db (SQLite + FTS5)
  WAL mode:    enabled
  Directories: config/, content/, ideas/, learnings/, backup/
  Status:      ready
```

$ARGUMENTS
