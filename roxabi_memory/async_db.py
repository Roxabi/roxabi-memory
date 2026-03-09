"""Async (aiosqlite) interface for roxabi-memory."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite

from .fts import search_fts_async
from .schema import MIGRATIONS, SCHEMA_V1_SQL


class AsyncMemoryDB:
    """Async (aiosqlite) wrapper. Use in asyncio-based Lyra agents."""

    def __init__(self, path: Path | str) -> None:
        self._path = path if isinstance(path, str) and path == ":memory:" else Path(path)
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open the aiosqlite connection with WAL mode and run schema migration."""
        path_str = self._path if isinstance(self._path, str) else str(self._path)

        self._db = await aiosqlite.connect(path_str)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._migrate()

    async def _migrate(self) -> None:
        """Apply SCHEMA_V1_SQL + incremental migrations via aiosqlite.

        SCHEMA_V1_SQL contains CREATE TRIGGER blocks with semicolons inside them,
        so we cannot split on ';'. Instead we dispatch executescript() to run on
        aiosqlite's own worker thread — the same thread that owns the connection.
        """
        db = self._db_or_raise()
        # Run executescript on the worker thread that owns the sqlite3 connection.
        await db._execute(db._conn.executescript, SCHEMA_V1_SQL)

        row = await (await db.execute("PRAGMA user_version")).fetchone()
        version: int = row[0] if row else 0
        for v in sorted(MIGRATIONS):
            if version >= v:
                continue
            for stmt in MIGRATIONS[v]:
                await db.execute(stmt)
            await db.execute(f"PRAGMA user_version = {v}")
            await db.commit()
            version = v

    def _db_or_raise(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("AsyncMemoryDB not connected — call connect() first")
        return self._db

    async def save_entry(
        self,
        content: str,
        type: str = "note",
        title: str = "",
        category: str = "general",
        namespace: str = "vault",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Insert an entry and return its new id (lastrowid)."""
        db = self._db_or_raise()
        try:
            metadata_str = json.dumps(metadata or {})
        except (TypeError, ValueError) as exc:
            raise ValueError(f"metadata is not JSON-serializable: {exc}") from exc
        cur = await db.execute(
            "INSERT INTO entries (category, type, title, content, namespace, metadata)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (category, type, title or content[:80], content, namespace, metadata_str),
        )
        await db.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid

    async def upsert_session(
        self,
        session_id: str,
        summary: str,
        **metadata_fields: Any,
    ) -> int:
        """Insert or update a session entry identified by session_id in metadata JSON.

        Returns the entry id.
        """
        db = self._db_or_raise()

        # Look up existing session entry by session_id stored in metadata JSON.
        async with db.execute(
            "SELECT id FROM entries"
            " WHERE json_extract(metadata, '$.session_id') = ?"
            "   AND type = 'session'",
            (session_id,),
        ) as cur:
            row = await cur.fetchone()

        meta = json.dumps({"session_id": session_id, **metadata_fields})

        if row is not None:
            entry_id: int = row[0]
            await db.execute(
                "UPDATE entries"
                " SET content = ?, metadata = ?, updated_at = datetime('now')"
                " WHERE id = ?",
                (summary, meta, entry_id),
            )
            await db.commit()
            return entry_id
        else:
            cur2 = await db.execute(
                "INSERT INTO entries"
                " (category, type, title, content, namespace, metadata)"
                " VALUES ('session', 'session', ?, ?, 'vault', ?)",
                (session_id, summary, meta),
            )
            await db.commit()
            assert cur2.lastrowid is not None
            return cur2.lastrowid

    async def search(
        self,
        query: str,
        namespace: str,
        limit: int = 5,
    ) -> list[dict]:
        """FTS5/BM25 search scoped to namespace (vault entries always included)."""
        return await search_fts_async(self._db_or_raise(), query, namespace, limit)

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def __aenter__(self) -> AsyncMemoryDB:
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
