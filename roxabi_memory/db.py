"""Sync SQLite interface for vault skills (sqlite3)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

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
        metadata: str = "{}",
    ) -> MemoryEntry:
        conn = self._conn_or_raise()
        cur = conn.execute(
            "INSERT INTO entries (category, type, title, content, namespace, metadata)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (category, type, title or content[:80], content, namespace, metadata),
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
