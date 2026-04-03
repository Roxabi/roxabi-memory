---
name: vault-init
description: 'Initialize the Roxabi vault — create ~/.roxabi-vault/ with SQLite+FTS5 database, subdirectories, and WAL mode. Triggers: "vault-init" | "init vault" | "setup vault" | "create vault" | "initialize vault".'
version: 0.2.0
allowed-tools: Bash, Read
---

# Vault Init

Let: DB=`~/.roxabi-vault/vault.db` | H=`~/.roxabi-vault/`

CLI: `vault` (via `roxabi-vault[cli]`). DB: DB.

## P1 — Check Existing

```bash
vault --json stats 2>&1 || echo "VAULT_NEW"
```

vault ∃ → report state; halt. ¬reinit.

## P2 — Initialize

```bash
vault init
```

Creates: H (700 | `$ROXABI_VAULT_HOME`); dirs: `config/ content/ ideas/ learnings/ backup/`; `vault.db` (schema v2, FTS5, WAL).

## P3 — Verify

```bash
vault --json stats
```

Confirm healthy; report: location, DB (SQLite+FTS5), WAL=on, dirs, status=ready.

$ARGUMENTS
