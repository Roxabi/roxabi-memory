---
name: vault-add
description: 'Store a new entry in the Roxabi vault — knowledge, notes, ideas, snippets, or references. Triggers: "vault add" | "add to vault" | "save this" | "store this" | "remember this" | "note this".'
version: 0.3.0
allowed-tools: Bash
---

# Vault Add

Let: DB=`~/.roxabi-vault/vault.db`

Store a new entry in DB.

## P1 — Check

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

¬ready → run `vault-init`; halt.

## P1.5 — URL Detection

input ∈ URL (`http/https`) → auto-invoke `web-intel:scrape`; use scraped (title, summary, key points) as content.
scrape fails ∨ web-intel ∄ → continue silently; category=`references`, type=`bookmark`.

## P2 — Infer Fields

¬user-specified → infer:

| Context | category | type |
|---------|----------|------|
| Ideas, brainstorms | `ideas` | `idea` |
| Code snippets | `content` | `snippet` |
| Lessons, insights | `learnings` | `learning` |
| Links, resources | `references` | `bookmark` |
| General notes | `notes` | `note` |

κ: `content` `ideas` `learnings` `notes` `references` | τ: `note` `idea` `learning` `snippet` `reference` `bookmark` | ∨ user-specified.

## P3 — Execute

```bash
vault put "<content>" --category "<category>" --type "<type>" --title "<title>"
```

Optional: `--metadata '{"key": "value"}'`.

## P4 — Report

Confirm with assigned entry ID.

$ARGUMENTS
