"""Schema definition and migration runner for roxabi-vault v3."""

from __future__ import annotations

import sqlite3

SCHEMA_V1_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    title, content, category, type,
    content=entries, content_rowid=id
);
CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, title, content, category, type)
    VALUES (new.id, new.title, new.content, new.category, new.type);
END;
CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, title, content, category, type)
    VALUES ('delete', old.id, old.title, old.content, old.category, old.type);
END;
CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, title, content, category, type)
    VALUES ('delete', old.id, old.title, old.content, old.category, old.type);
    INSERT INTO entries_fts(rowid, title, content, category, type)
    VALUES (new.id, new.title, new.content, new.category, new.type);
END;
"""

MIGRATIONS: dict[int, list[str]] = {
    2: [
        "ALTER TABLE entries ADD COLUMN namespace TEXT NOT NULL DEFAULT 'vault'",
        "ALTER TABLE entries ADD COLUMN embedding BLOB",
        "ALTER TABLE entries ADD COLUMN source_turns TEXT",
        "ALTER TABLE entries ADD COLUMN event_date TEXT",
    ],
    3: [
        """CREATE TABLE IF NOT EXISTS entry_tags (
            entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            tag TEXT NOT NULL,
            PRIMARY KEY (entry_id, tag)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_entry_tags_tag ON entry_tags(tag)",
        "CREATE INDEX IF NOT EXISTS idx_entry_tags_entry ON entry_tags(entry_id)",
    ],
}

TARGET_VERSION = max(MIGRATIONS)


def migrate(conn: sqlite3.Connection) -> None:
    """Run schema migrations idempotently. Safe to call on every connect."""
    conn.executescript(SCHEMA_V1_SQL)
    version: int = conn.execute("PRAGMA user_version").fetchone()[0]
    for v in sorted(MIGRATIONS):
        if version >= v:
            continue
        for stmt in MIGRATIONS[v]:
            conn.execute(stmt)
        conn.execute(f"PRAGMA user_version = {v}")
        conn.commit()
        version = v
