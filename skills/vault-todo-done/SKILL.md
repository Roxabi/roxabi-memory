---
name: vault-todo-done
description: 'Mark a todo done by deleting it from the vault. Triggers: "todo done" | "done todo" | "done <id>" | "complete todo" | "finish todo" | "vault todo done" | "remove todo".'
version: 0.1.0
allowed-tools: Bash
---

# Vault Todo Done

Let: DB=`~/.roxabi-vault/vault.db` | κ=`todo`

Complete a todo = delete the entry. No state, no archive — gone.

## P1 — Check

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

¬ready → run `vault-init`; halt.

## P2 — Resolve ID

∄ ID → run `vault list --category todo --limit 50` then ask user which ID.

entry κ ≠ `todo` → refuse; say "not a todo — use vault-delete"; halt.

## P3 — Execute

```bash
vault delete <id> -y
```

`-y` = skip confirm (low-stakes, easy to re-add).

## P4 — Report

Confirm: `✓ done #<id> — <title>`.

$ARGUMENTS
