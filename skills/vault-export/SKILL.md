---
name: vault-export
description: 'Export vault entries as JSON, optionally filtered by category or namespace. Triggers: "vault export" | "export vault" | "export entries" | "dump vault" | "backup vault".'
version: 0.2.0
allowed-tools: Bash
---

# Vault Export

Let: DB=`~/.roxabi-vault/vault.db`

Export entries from DB as JSON.

## P1 — Check

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

¬ready → run `vault-init`; halt.

## P2 — Execute

```bash
vault export --category "<category>" --namespace "<namespace>" -o "<path>"
```

All filters optional. ∄ path → display JSON inline. ∃ path → confirm location.

## P3 — Report

Confirm: entry count + output location (or display JSON).

$ARGUMENTS
