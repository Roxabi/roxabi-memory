---
name: vault-export
description: 'Export vault entries as JSON, optionally filtered by category or namespace. Triggers: "vault export" | "export vault" | "export entries" | "dump vault" | "backup vault".'
version: 0.2.0
allowed-tools: Bash
---

# Vault Export

Export entries from the Roxabi vault (`~/.roxabi-vault/vault.db`) as JSON.

## Phase 1 — Check Vault

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

If not ready, tell the user to run `vault-init` first. Stop here.

## Phase 2 — Execute

```bash
vault export --category "<category>" --namespace "<namespace>" -o "<path>"
```

All filters are optional. If no output path was given, display the JSON inline. If a path was given, confirm the export location first.

## Phase 3 — Report

Confirm the number of entries exported and the output location (or display the JSON).

$ARGUMENTS
