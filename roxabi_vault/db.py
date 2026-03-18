"""Sync SQLite interface for vault skills (sqlite3)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import migrate


@dataclass
class MemoryEntry:
    id: int
    category: str
    type: str
    title: str
    content: str
    namespace: str
    metadata: str
    created_at: str
    updated_at: str


class MemoryDB:
    """Sync (sqlite3) wrapper. Use in Claude Code skills only."""

    def __init__(self, path: Path | str) -> None:
        self._path = (
            path if isinstance(path, str) and path == ":memory:" else Path(path)
        )
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        path_str = self._path if isinstance(self._path, str) else str(self._path)
        self._conn = sqlite3.connect(path_str)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        migrate(self._conn)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> MemoryDB:
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def connection(self) -> sqlite3.Connection:
        """Expose the raw connection for advanced consumers (e.g. shared-connection adapters)."""
        if self._conn is None:
            raise RuntimeError("MemoryDB not connected — call connect() first")
        return self._conn

    def _conn_or_raise(self) -> sqlite3.Connection:
        return self.connection

    def save_entry(
        self,
        content: str,
        type: str = "note",
        title: str = "",
        category: str = "general",
        namespace: str = "vault",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        conn = self._conn_or_raise()
        try:
            metadata_str = json.dumps(metadata or {})
        except (TypeError, ValueError) as exc:
            raise ValueError(f"metadata is not JSON-serializable: {exc}") from exc
        cur = conn.execute(
            "INSERT INTO entries (category, type, title, content, namespace, metadata)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (category, type, title or content[:80], content, namespace, metadata_str),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM entries WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return self._row(row)

    def search_fts(
        self, query: str, namespace: str | None = None, limit: int = 20
    ) -> list[MemoryEntry]:
        conn = self._conn_or_raise()
        safe_q = '"' + query.replace('"', '""').replace("*", "").replace("^", "") + '"'
        sql = """
            SELECT e.* FROM entries_fts fts
            JOIN entries e ON e.id = fts.rowid
            WHERE entries_fts MATCH ?
        """
        params: list[object] = [safe_q]
        if namespace:
            sql += " AND (e.namespace = ? OR e.namespace = 'vault')"
            params.append(namespace)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)
        return [self._row(r) for r in conn.execute(sql, params).fetchall()]

    def get_entry(self, id: int) -> MemoryEntry | None:
        conn = self._conn_or_raise()
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (id,)).fetchone()
        return self._row(row) if row else None

    def delete_entry(self, id: int) -> bool:
        conn = self._conn_or_raise()
        cur = conn.execute("DELETE FROM entries WHERE id = ?", (id,))
        conn.commit()
        return cur.rowcount > 0

    def list_entries(
        self,
        namespace: str | None = None,
        category: str | None = None,
        limit: int | None = 50,
        offset: int = 0,
    ) -> list[MemoryEntry]:
        if limit is None and offset:
            raise ValueError("offset requires limit")
        conn = self._conn_or_raise()
        sql = "SELECT * FROM entries WHERE 1=1"
        params: list[object] = []
        if namespace:
            sql += " AND namespace = ?"
            params.append(namespace)
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY id"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
            if offset:
                sql += " OFFSET ?"
                params.append(offset)
        return [self._row(r) for r in conn.execute(sql, params).fetchall()]

    def get_stats(self) -> dict:
        conn = self._conn_or_raise()
        count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        namespaces = [
            r[0]
            for r in conn.execute("SELECT DISTINCT namespace FROM entries").fetchall()
        ]
        categories = [
            r[0]
            for r in conn.execute("SELECT DISTINCT category FROM entries").fetchall()
        ]
        return {"count": count, "namespaces": namespaces, "categories": categories}

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def set_tags(self, entry_id: int, tags: list[str]) -> None:
        """Replace all tags for an entry (idempotent)."""
        conn = self._conn_or_raise()
        conn.execute("DELETE FROM entry_tags WHERE entry_id = ?", (entry_id,))
        cleaned = [(entry_id, t.lower().strip()) for t in tags if t.strip()]
        if cleaned:
            conn.executemany(
                "INSERT OR IGNORE INTO entry_tags (entry_id, tag) VALUES (?, ?)",
                cleaned,
            )
        conn.commit()

    def add_tags(self, entry_id: int, tags: list[str]) -> None:
        """Add tags to an entry without removing existing ones."""
        conn = self._conn_or_raise()
        cleaned = [(entry_id, t.lower().strip()) for t in tags if t.strip()]
        if cleaned:
            conn.executemany(
                "INSERT OR IGNORE INTO entry_tags (entry_id, tag) VALUES (?, ?)",
                cleaned,
            )
            conn.commit()

    def get_tags(self, entry_id: int) -> list[str]:
        """Get all tags for a specific entry."""
        conn = self._conn_or_raise()
        rows = conn.execute(
            "SELECT tag FROM entry_tags WHERE entry_id = ? ORDER BY tag",
            (entry_id,),
        ).fetchall()
        return [r[0] for r in rows]

    def entries_by_tag(self, tag: str, limit: int = 50) -> list[MemoryEntry]:
        """Find entries with a specific tag."""
        conn = self._conn_or_raise()
        rows = conn.execute(
            """SELECT e.* FROM entries e
               JOIN entry_tags t ON t.entry_id = e.id
               WHERE t.tag = ?
               ORDER BY e.id LIMIT ?""",
            (tag.lower().strip(), limit),
        ).fetchall()
        return [self._row(r) for r in rows]

    def all_tags(self) -> list[tuple[str, int]]:
        """Return all tags with entry count, sorted by frequency desc."""
        conn = self._conn_or_raise()
        rows = conn.execute(
            "SELECT tag, COUNT(*) FROM entry_tags GROUP BY tag ORDER BY COUNT(*) DESC"
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    def tagged_entry_ids(self) -> set[int]:
        """Return set of entry IDs that have at least one tag."""
        conn = self._conn_or_raise()
        rows = conn.execute("SELECT DISTINCT entry_id FROM entry_tags").fetchall()
        return {r[0] for r in rows}

    def _row(self, row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            category=row["category"],
            type=row["type"],
            title=row["title"],
            content=row["content"],
            namespace=row["namespace"],
            metadata=row["metadata"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
