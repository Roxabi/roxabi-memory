# Architecture

Overview of roxabi-memory's architecture, modules, and design decisions.

## High-Level Overview

roxabi-memory is a Python library that provides persistent, structured memory storage backed by SQLite. It is designed as the memory backend for Lyra agents and vault skills.

```
┌─────────────────────────────────────────────────┐
│                   Consumers                      │
│  (Lyra agents, vault skills, CLI users)          │
├──────────┬──────────┬───────────────────────────-┤
│  rmem    │ Namespaced│  Direct API               │
│  CLI     │ Wrappers  │  (sync / async)           │
│ (Typer)  │ (R/W)     │                           │
├──────────┴──────────┴───────────────────────────-┤
│              MemoryDB / AsyncMemoryDB            │
│         (CRUD, FTS search, session upsert)       │
├─────────────────────────────────────────────────-┤
│          schema.py — migrations & DDL            │
├─────────────────────────────────────────────────-┤
│     SQLite (WAL mode) + FTS5 full-text index     │
└─────────────────────────────────────────────────-┘
```

## Module Map

| Module | Responsibility |
|---|---|
| `schema.py` | DDL (tables, FTS5 virtual table, triggers) and incremental migration runner |
| `db.py` | Sync `MemoryDB` class — CRUD operations + FTS search using `sqlite3` |
| `async_db.py` | Async `AsyncMemoryDB` class — same operations via `aiosqlite`, plus `upsert_session()` |
| `fts.py` | Shared FTS5/BM25 search SQL and query sanitization (sync + async variants) |
| `namespace.py` | `NamespacedReader` / `NamespacedWriter` — scoped access wrappers around `AsyncMemoryDB` |
| `cli.py` | `rmem` CLI built with Typer + Rich — exposes all CRUD operations as shell commands |

## Data Model

Each memory entry is stored in the `entries` table:

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY` | Auto-incrementing ID |
| `category` | `TEXT NOT NULL` | Grouping tag (e.g. `"general"`, `"session"`) |
| `type` | `TEXT NOT NULL` | Entry type (e.g. `"note"`, `"session"`) |
| `title` | `TEXT NOT NULL` | Short title (defaults to first 80 chars of content) |
| `content` | `TEXT NOT NULL` | Full content body |
| `namespace` | `TEXT NOT NULL` | Isolation scope (default `"vault"`) |
| `metadata` | `TEXT DEFAULT '{}'` | Arbitrary JSON blob |
| `embedding` | `BLOB` | Vector embedding (reserved, not yet wired) |
| `source_turns` | `TEXT` | Source conversation turns (reserved) |
| `event_date` | `TEXT` | Optional date associated with the entry |
| `created_at` | `TEXT` | ISO timestamp, set on insert |
| `updated_at` | `TEXT` | ISO timestamp, set on insert |

A companion `entries_fts` FTS5 virtual table indexes `title`, `content`, `category`, and `type` for full-text search. Triggers keep the FTS index in sync on INSERT, UPDATE, and DELETE.

## Key Design Decisions

- **SQLite + WAL mode**: Single-file database, no server needed. WAL allows concurrent readers.
- **FTS5 for search**: Built-in full-text search via SQLite's FTS5 extension — no external search engine required.
- **Namespace isolation**: Entries are scoped by namespace. Searches always include the `"vault"` namespace alongside the requested one.
- **Sync + async APIs**: `MemoryDB` (sqlite3) for simple scripts and CLI; `AsyncMemoryDB` (aiosqlite) for async agent runtimes.
- **Idempotent migrations**: `schema.migrate()` is called on every connection and is safe to run repeatedly.
- **Optional dependencies**: Core requires only `aiosqlite`. CLI (`typer`, `rich`) and embeddings (`fastembed`, `sqlite-vec`) are optional extras.

## Future: Hybrid Search

Issue #7 tracks adding vector/semantic search using `fastembed` (ONNX embeddings) + `sqlite-vec`, to be combined with the existing FTS5 keyword search into a hybrid ranking.
