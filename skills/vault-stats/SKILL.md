---
name: vault-stats
description: 'Show statistics for the Roxabi vault — entry counts, categories, and database info. Triggers: "vault stats" | "vault status" | "how many entries" | "vault info" | "vault summary".'
version: 0.2.0
allowed-tools: Bash
---

# Vault Stats

Show statistics for `~/.roxabi-vault/vault.db`.

## P1 — Execute

```bash
vault stats
```

¬ready → run `vault-init`.

## P2 — Report

Summary: total entries, breakdown by category, DB location.

$ARGUMENTS
