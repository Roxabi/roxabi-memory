"""Namespace-scoped read/write wrappers for AsyncMemoryDB."""
from __future__ import annotations

from .async_db import AsyncMemoryDB


class NamespacedReader:
    """Read-only view scoped to a namespace (vault entries are always visible)."""

    def __init__(self, db: AsyncMemoryDB, namespace: str) -> None:
        self._db = db
        self._namespace = namespace

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        return await self._db.search(query, self._namespace, limit)


class NamespacedWriter:
    """Write-only view scoped to a namespace."""

    def __init__(self, db: AsyncMemoryDB, namespace: str) -> None:
        self._db = db
        self._namespace = namespace

    async def save(
        self,
        content: str,
        type: str = "note",
        title: str = "",
        metadata: str = "{}",
    ) -> int:
        return await self._db.save_entry(
            content=content,
            type=type,
            title=title,
            namespace=self._namespace,
            metadata=metadata,
        )
