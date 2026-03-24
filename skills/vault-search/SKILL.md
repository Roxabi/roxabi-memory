---
name: vault-search
description: 'Find entries in the Roxabi vault by keyword or phrase using FTS5 full-text search. Triggers: "vault search" | "search vault" | "find in vault" | "look up" | "search for".'
version: 0.2.0
allowed-tools: Bash
---

# Vault Search

FTS5 full-text search over `~/.roxabi-vault/vault.db`.

## P1 — Check

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

¬ready → run `vault-init`; halt.

## P2 — Execute

```bash
vault search "<query>" --limit <N>
```

Default limit: 10.

## P3 — Report

Table: ID | Category | Type | Title | Created.
¬results → say so; suggest broadening query.

$ARGUMENTS
