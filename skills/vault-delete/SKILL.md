---
name: vault-delete
description: 'Delete a vault entry by ID after confirmation. Triggers: "vault delete" | "delete entry" | "remove entry" | "delete id" | "remove from vault".'
version: 0.2.0
allowed-tools: Bash
---

# Vault Delete

Remove an entry from the Roxabi vault (`~/.roxabi-vault/vault.db`).

## Phase 1 — Check Vault

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

If not ready, tell the user to run `vault-init` first. Stop here.

## Phase 2 — Show Entry

Fetch and display the entry before deleting:

```bash
vault get <id>
```

If the user did not provide an ID, ask for it. If the entry does not exist, say so and stop.

## Phase 3 — Confirm

Ask for confirmation using `AskUserQuestion` before proceeding. Show the entry title and ID in the question.

## Phase 4 — Execute

```bash
vault delete <id>
```

## Phase 5 — Report

Confirm the entry was deleted by ID and title.

$ARGUMENTS
