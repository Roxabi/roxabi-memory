---
name: vault-add
description: 'Store a new entry in the Roxabi vault — knowledge, notes, ideas, snippets, or references. Triggers: "vault add" | "add to vault" | "save this" | "store this" | "remember this" | "note this".'
version: 0.2.0
allowed-tools: Bash
---

# Vault Add

Store a new entry in the Roxabi vault (`~/.roxabi-vault/vault.db`).

## Phase 1 — Check Vault

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

If not ready, tell the user to run `vault-init` first. Stop here.

## Phase 2 — Infer Fields

If the user did not specify category/type, infer from context:

| Context | category | type |
|---------|----------|------|
| Ideas, brainstorms | `ideas` | `idea` |
| Code snippets, patterns | `content` | `snippet` |
| Lessons, insights | `learnings` | `learning` |
| Links, resources | `references` | `bookmark` |
| General notes | `notes` | `note` |

Valid categories: `content`, `ideas`, `learnings`, `notes`, `references`, or user-specified.
Valid types: `note`, `idea`, `learning`, `snippet`, `reference`, `bookmark`, or user-specified.

## Phase 3 — Execute

```bash
vault put "<content>" --category "<category>" --type "<type>" --title "<title>"
```

Optional: `--metadata '{"key": "value"}'` for structured metadata.

## Phase 4 — Report

Confirm the operation with the assigned entry ID.

$ARGUMENTS
