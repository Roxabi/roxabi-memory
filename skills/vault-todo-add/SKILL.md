---
name: vault-todo-add
description: 'Add a todo/follow-up note to the vault — fast capture, no state, just content. Triggers: "add todo" | "todo:" | "new todo" | "track this" | "follow up" | "remind me to" | "vault todo add".'
version: 0.1.0
allowed-tools: Bash
---

# Vault Todo Add

Let: DB=`~/.roxabi-vault/vault.db` | κ=`todo` | τ=`task`

Capture a todo/follow-up as a vault entry. ¬status, ¬due, ¬priority — just content. Removal = `vault-todo-done`.

## P1 — Check

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

¬ready → run `vault-init`; halt.

## P2 — Extract Content

∄ content → ask user what to track. Strip leading "todo:" / "todo " / "remind me to" if present.

## P3 — Execute

```bash
vault put "<content>" --category todo --type task --title "<content first 80 chars>"
```

Title auto-inferred if ¬specified.

## P4 — Report

Confirm: `✓ todo #<id> — <title>`.

$ARGUMENTS
