---
name: vault-delete
description: 'Delete a vault entry by ID after confirmation. Triggers: "vault delete" | "delete entry" | "remove entry" | "delete id" | "remove from vault".'
version: 0.2.0
allowed-tools: Bash
---

# Vault Delete

Let: DB=`~/.roxabi-vault/vault.db`

Remove an entry from DB.

## P1 — Check

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

¬ready → run `vault-init`; halt.

## P2 — Show Entry

∄ ID → ask. ∄ entry → say so; halt.

```bash
vault get <id>
```

## P3 — Confirm

`AskUserQuestion` with entry title + ID before proceeding.

## P4 — Execute

```bash
vault delete <id>
```

## P5 — Report

Confirm deletion by ID and title.

$ARGUMENTS
