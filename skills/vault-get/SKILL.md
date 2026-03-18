---
name: vault-get
description: 'Get full details of a specific vault entry by ID. Triggers: "vault get" | "show entry" | "get entry" | "fetch entry" | "show id".'
version: 0.2.0
allowed-tools: Bash
---

# Vault Get

Retrieve full details of a vault entry by ID.

## P1 — Check

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

¬ready → run `vault-init`; halt.

## P2 — Execute

∄ ID → ask for it.

```bash
vault get <id>
```

## P3 — Report

All fields: id, title, content, category, type, namespace, metadata, created, updated.

$ARGUMENTS
