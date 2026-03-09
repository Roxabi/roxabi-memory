# Ubiquitous Language

Glossary of domain terms used in roxabi-memory. Keeps agents and contributors aligned on vocabulary.

## Glossary

| Term | Definition | Source |
|------|-----------|--------|
| Entry | A single record in the `entries` table — the atomic unit of stored memory. Has content, title, category, type, namespace, and metadata. | `db.py`, `schema.py` |
| Namespace | An isolation scope for entries. Searches are scoped to the requested namespace plus `"vault"`. Default namespace is `"vault"`. | `namespace.py`, `fts.py` |
| Vault | The default namespace (`"vault"`). Entries in vault are always visible across all namespace-scoped searches. Acts as shared/global memory. | `db.py`, `fts.py` |
| Category | A grouping tag on an entry (e.g. `"general"`, `"session"`). Used for filtering, not access control. | `schema.py` |
| Type | The kind of entry (e.g. `"note"`, `"session"`). Stored as a text field, not an enum. | `schema.py` |
| FTS / Full-Text Search | SQLite FTS5-based keyword search with BM25 ranking. Indexes title, content, category, and type. | `fts.py` |
| Session | A special entry type used by `AsyncMemoryDB.upsert_session()` to track conversation sessions. Identified by `session_id` in the metadata JSON. | `async_db.py` |
| Migration | An incremental schema change tracked by `PRAGMA user_version`. Applied automatically on connect. | `schema.py` |
| MemoryDB | The sync (sqlite3) database wrapper. Used in CLI and simple scripts. | `db.py` |
| AsyncMemoryDB | The async (aiosqlite) database wrapper. Used in asyncio-based Lyra agents. | `async_db.py` |
| NamespacedReader | A read-only view scoped to a specific namespace. Wraps `AsyncMemoryDB.search()`. | `namespace.py` |
| NamespacedWriter | A write-only view scoped to a specific namespace. Wraps `AsyncMemoryDB.save_entry()`. | `namespace.py` |
| Lyra | The agent runtime that consumes roxabi-memory as its persistence layer. | `__init__.py` |

## Common Confusions

| Confused terms | Clarification |
|---|---|
| namespace vs. category | **Namespace** controls search isolation (entries in `vault` are always visible). **Category** is just a label for filtering — it has no access control implications. |
| type vs. category | **Type** describes what the entry is (`"note"`, `"session"`). **Category** describes what it's about (`"general"`, `"debugging"`). Both are free-form text. |
| MemoryDB vs. AsyncMemoryDB | Same operations, different runtimes. `MemoryDB` uses `sqlite3` (sync), `AsyncMemoryDB` uses `aiosqlite` (async). The async variant also has `upsert_session()`. |
| vault (namespace) vs. vault (skill) | The **vault namespace** is the default namespace in the database. The **vault skill** is a consumer of roxabi-memory (a Claude Code skill that uses this library). |
