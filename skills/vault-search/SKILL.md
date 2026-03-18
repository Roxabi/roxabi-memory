---
name: vault-search
description: 'Find entries in the Roxabi vault by keyword or phrase using FTS5 full-text search. Triggers: "vault search" | "search vault" | "find in vault" | "look up" | "search for".'
version: 0.2.0
allowed-tools: Bash
---

# Vault Search

Search the Roxabi vault (`~/.roxabi-vault/vault.db`) using full-text search.

## Phase 1 — Check Vault

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

If not ready, tell the user to run `vault-init` first. Stop here.

## Phase 2 — Execute

```bash
vault search "<query>" --limit <N>
```

Default limit: 10. Use the user's query as-is.

## Phase 3 — Report

Present results as a readable table:

```
ID  | Category  | Type     | Title                  | Created
----|-----------|----------|------------------------|-------------------
1   | learnings | learning | SQLite WAL advantages  | 2024-01-15 10:30
```

If no results, say so clearly and suggest broadening the query.

$ARGUMENTS
