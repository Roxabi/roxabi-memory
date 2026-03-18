"""Async (aiosqlite) interface for roxabi-vault."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import aiosqlite

from .fts import search_fts_async
from .schema import MIGRATIONS, SCHEMA_V1_SQL

logger = logging.getLogger(__name__)


class AsyncMemoryDB:
    """Async (aiosqlite) wrapper. Use in asyncio-based Lyra agents."""

    def __init__(self, path: Path | str, *, embeddings: bool = False) -> None:
        self._path = (
            path if isinstance(path, str) and path == ":memory:" else Path(path)
        )
        self._db: aiosqlite.Connection | None = None
        self._embeddings = embeddings
        self._embedder = None
        self._background_tasks: set[asyncio.Task] = set()

        if embeddings:
            try:
                from .embeddings import Embedder  # noqa: F811 — import guard
            except ImportError as exc:
                raise ImportError(
                    "Embeddings require fastembed and sqlite-vec: "
                    "pip install roxabi-vault[embeddings]"
                ) from exc
            # Store class for deferred init in connect() via run_in_executor
            self._embedder_cls = Embedder

    async def connect(self) -> None:
        """Open the aiosqlite connection with WAL mode and run schema migration."""
        path_str = self._path if isinstance(self._path, str) else str(self._path)

        self._db = await aiosqlite.connect(path_str)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._migrate()

        if self._embeddings:
            await self._load_sqlite_vec()
            # Load ONNX model off the event loop thread
            loop = asyncio.get_running_loop()
            self._embedder = await loop.run_in_executor(None, self._embedder_cls)

    async def _load_sqlite_vec(self) -> None:
        """Load the sqlite-vec extension on the aiosqlite worker thread."""
        db = self._db_or_raise()
        try:
            import sqlite_vec

            await db._execute(sqlite_vec.load, db._conn)
        except Exception as exc:
            raise RuntimeError(
                "sqlite-vec extension failed to load — "
                "Python may lack extension support or sqlite-vec is not installed. "
                f"Original error: {exc}"
            ) from exc

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

    async def _embed_if_enabled(self, text: str) -> bytes | None:
        """Return embedding bytes if embeddings are enabled, else None."""
        if self._embeddings and self._embedder is not None:
            return await self._embedder.embed_async(text)
        return None

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

        embedding = await self._embed_if_enabled(content)
        cur = await db.execute(
            "INSERT INTO entries (category, type, title, content, namespace, metadata, embedding)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                category,
                type,
                title or content[:80],
                content,
                namespace,
                metadata_str,
                embedding,
            ),
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
        embedding = await self._embed_if_enabled(summary)

        if row is not None:
            entry_id: int = row[0]
            await db.execute(
                "UPDATE entries"
                " SET content = ?, metadata = ?, embedding = ?,"
                " updated_at = datetime('now')"
                " WHERE id = ?",
                (summary, meta, embedding, entry_id),
            )
            await db.commit()
            return entry_id
        else:
            cur2 = await db.execute(
                "INSERT INTO entries"
                " (category, type, title, content, namespace, metadata, embedding)"
                " VALUES ('session', 'session', ?, ?, 'vault', ?, ?)",
                (session_id, summary, meta, embedding),
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
        """Search scoped to namespace. Hybrid (BM25+cosine) when embeddings enabled."""
        db = self._db_or_raise()

        if self._embeddings and self._embedder is not None:
            from .search import hybrid_search

            results = await hybrid_search(db, self._embedder, query, namespace, limit)
            # Find result IDs that have NULL embedding via a targeted query
            result_ids = [r["id"] for r in results]
            if result_ids:
                placeholders = ",".join("?" * len(result_ids))
                async with db.execute(
                    f"SELECT id FROM entries WHERE id IN ({placeholders})"
                    " AND embedding IS NULL",
                    result_ids,
                ) as cur:
                    null_ids = [row[0] for row in await cur.fetchall()]
                if null_ids:
                    task = asyncio.create_task(self._backfill_entries(null_ids))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
            return results

        return await search_fts_async(db, query, namespace, limit)

    async def _backfill_entries(self, entry_ids: list[int]) -> None:
        """Backfill embeddings for entries with NULL embedding. Best-effort."""
        try:
            db = self._db_or_raise()
            if not entry_ids or self._embedder is None:
                return
            # Batch fetch all entries needing backfill in a single query.
            placeholders = ",".join("?" * len(entry_ids))
            async with db.execute(
                f"SELECT id, content FROM entries"
                f" WHERE id IN ({placeholders}) AND embedding IS NULL",
                entry_ids,
            ) as cur:
                rows = await cur.fetchall()
            for eid, content in rows:
                embedding = await self._embedder.embed_async(content)
                await db.execute(
                    "UPDATE entries SET embedding = ? WHERE id = ?",
                    (embedding, eid),
                )
            if rows:
                await db.commit()
        except (aiosqlite.OperationalError, ValueError, OSError):
            logger.warning("Backfill failed for entries %s", entry_ids, exc_info=True)

    async def close(self) -> None:
        # Cancel any in-flight backfill tasks before closing the connection.
        for task in self._background_tasks:
            task.cancel()
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def __aenter__(self) -> AsyncMemoryDB:
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
