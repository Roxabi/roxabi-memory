---
name: vault-todo-list
description: 'List open todos/follow-ups from the vault. Triggers: "list todos" | "show todos" | "todos" | "what are my todos" | "pending todos" | "vault todo list".'
version: 0.1.0
allowed-tools: Bash
---

# Vault Todo List

Let: DB=`~/.roxabi-vault/vault.db` | κ=`todo`

Show all open todos (everything ∈ κ=todo). Removal = `vault-todo-done`.

## P1 — Check

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

¬ready → run `vault-init`; halt.

## P2 — Execute

```bash
vault list --category todo --limit 50
```

User-specified limit → override.

## P3 — Report

Table: id · title · created. ¬matches → say "no open todos".

$ARGUMENTS
