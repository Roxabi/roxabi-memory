---
name: vault-add
description: 'Store a new entry in the Roxabi vault — knowledge, notes, ideas, snippets, or references. Triggers: "vault add" | "add to vault" | "save this" | "store this" | "remember this" | "note this".'
version: 0.3.0
allowed-tools: Bash
---

# Vault Add

Store a new entry in the Roxabi vault (`~/.roxabi-vault/vault.db`).

## Phase 1 — Check Vault

```bash
vault stats 2>&1 || echo "VAULT_NOT_READY"
```

If not ready, tell the user to run `vault-init` first. Stop here.

## Phase 1.5 — URL Detection

If the input looks like a URL (starts with `http://` or `https://`):

- Check if the `web-intel:scrape` skill is available (look for it in the skills list or assume it's available if `web-intel` plugin is installed).
- If available, recommend it:

  > "This looks like a URL. The `web-intel:scrape` skill can extract structured content (title, summary, key points) before vaulting — use `/scrape <url>` then `vault add` the result for richer storage. Proceed with raw URL? [yes/no]"

  Use `AskUserQuestion` with options: **Scrape first** | **Store URL as-is**.
  - If "Scrape first" → stop here, instruct the user to run `/scrape <url>` first, then vault the result.
  - If "Store URL as-is" → continue to Phase 2 with category=`references`, type=`bookmark`.

- If `web-intel` is not available → skip this phase silently and continue.

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
