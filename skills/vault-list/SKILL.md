---
name: vault-list
description: 'Browse entries in the Roxabi vault with optional category/namespace filters. Triggers: "vault list" | "list vault" | "show entries" | "browse vault" | "list all".'
version: 0.2.0
allowed-tools: Bash
---

# Vault List

Browse entries in `~/.roxabi-vault/vault.db`.

## P1 — Check

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

¬ready → run `vault-init`; halt.

## P2 — Execute

```bash
vault list --category "<category>" --namespace "<namespace>" --limit <N>
```

All filters optional. ¬filters → list all (default limit: 20).

## P3 — Report

Table: id, title, category, type, created. ¬matches → say so.

$ARGUMENTS
