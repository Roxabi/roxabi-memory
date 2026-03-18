---
name: vault-get
description: 'Get full details of a specific vault entry by ID. Triggers: "vault get" | "show entry" | "get entry" | "fetch entry" | "show id".'
version: 0.2.0
allowed-tools: Bash
---

# Vault Get

Retrieve the full details of a specific vault entry by its ID.

## Phase 1 — Check Vault

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

If not ready, tell the user to run `vault-init` first. Stop here.

## Phase 2 — Execute

```bash
vault get <id>
```

If the user did not provide an ID, ask for it.

## Phase 3 — Report

Display the full entry with all fields: id, title, content, category, type, namespace, metadata, created, and updated.

$ARGUMENTS
