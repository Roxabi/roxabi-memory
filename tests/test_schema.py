"""Tests for roxabi_memory.schema — migrate() and schema correctness."""
import sqlite3

import pytest

from roxabi_memory.schema import TARGET_VERSION, migrate


def make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_migrate_fresh_db() -> None:
    # Arrange
    conn = make_conn()

    # Act
    migrate(conn)

    # Assert — user_version is bumped to TARGET_VERSION
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == TARGET_VERSION

    # Assert — v2 columns exist
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(entries)")}
    assert {"namespace", "embedding", "source_turns", "event_date"} <= cols


def test_migrate_idempotent() -> None:
    # Arrange
    conn = make_conn()
    migrate(conn)

    # Act — second call must not raise
    migrate(conn)

    # Assert
    assert conn.execute("PRAGMA user_version").fetchone()[0] == TARGET_VERSION


def test_migrate_v1_db_preserves_existing_rows() -> None:
    """A v1 DB that already has rows must keep them after migration to v2."""
    # Arrange — build v1 schema manually with defaults so the INSERT works
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL DEFAULT 'general',
            type TEXT NOT NULL DEFAULT 'note',
            title TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        INSERT INTO entries (content) VALUES ('existing entry');
        PRAGMA user_version = 1;
    """)

    # Act
    migrate(conn)

    # Assert — existing row is intact and gets the DEFAULT namespace
    rows = conn.execute("SELECT content, namespace FROM entries").fetchall()
    assert len(rows) == 1
    assert rows[0]["content"] == "existing entry"
    assert rows[0]["namespace"] == "vault"


def test_fts5_triggers_work() -> None:
    # Arrange
    conn = make_conn()
    migrate(conn)

    # Act
    conn.execute(
        "INSERT INTO entries (category, type, title, content)"
        " VALUES ('g', 'n', 'Python', 'Mickael prefers Python')"
    )
    conn.commit()

    # Assert — FTS index is populated via the AFTER INSERT trigger
    rows = conn.execute(
        "SELECT * FROM entries_fts WHERE entries_fts MATCH '\"Python\"'"
    ).fetchall()
    assert rows


def test_v2_columns_have_correct_defaults() -> None:
    """namespace defaults to 'vault'; embedding/source_turns/event_date default to NULL."""
    # Arrange
    conn = make_conn()
    migrate(conn)

    # Act
    conn.execute(
        "INSERT INTO entries (category, type, title, content)"
        " VALUES ('g', 'n', 't', 'content')"
    )
    conn.commit()
    row = conn.execute("SELECT * FROM entries").fetchone()

    # Assert
    assert row["namespace"] == "vault"
    assert row["embedding"] is None
    assert row["source_turns"] is None
    assert row["event_date"] is None
