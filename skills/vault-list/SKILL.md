---
name: vault-list
description: 'Browse entries in the Roxabi vault with optional category/namespace filters. Triggers: "vault list" | "list vault" | "show entries" | "browse vault" | "list all".'
version: 0.2.0
allowed-tools: Bash
---

# Vault List

Browse entries in the Roxabi vault (`~/.roxabi-vault/vault.db`).

## Phase 1 — Check Vault

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

If not ready, tell the user to run `vault-init` first. Stop here.

## Phase 2 — Execute

```bash
vault list --category "<category>" --namespace "<namespace>" --limit <N>
```

All filters are optional. If the user specifies no filters, list all entries (default limit: 20).

## Phase 3 — Report

Present results as a table with id, title, category, type, and created date. If no entries match, say so.

$ARGUMENTS
