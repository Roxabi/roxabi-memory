---
name: vault-stats
description: 'Show statistics for the Roxabi vault — entry counts, categories, and database info. Triggers: "vault stats" | "vault status" | "how many entries" | "vault info" | "vault summary".'
version: 0.2.0
allowed-tools: Bash
---

# Vault Stats

Show statistics for the Roxabi vault (`~/.roxabi-vault/vault.db`).

## Phase 1 — Execute

```bash
vault stats
```

If vault is not ready (error), tell the user to run `vault-init` first.

## Phase 2 — Report

Format the output as a readable summary with total entries, breakdown by category, and database location.

$ARGUMENTS
