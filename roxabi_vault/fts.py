"""FTS5/BM25 keyword search — sync and async variants."""

from __future__ import annotations

import re
import sqlite3

import aiosqlite


def _safe_query(q: str) -> str:
    """Sanitise FTS5 query: tokenize and quote each term (AND semantics)."""
    terms = re.sub(r'[*^"]+', " ", q).split()
    return " ".join(f'"{t}"' for t in terms if t)


_SEARCH_SQL = """
    SELECT e.id, e.category, e.type, e.title, e.content,
           e.namespace, e.metadata, e.created_at, e.updated_at, rank
    FROM entries_fts fts
    JOIN entries e ON e.id = fts.rowid
    WHERE entries_fts MATCH ?
      AND (e.namespace = ? OR e.namespace = 'vault')
    ORDER BY rank
    LIMIT ?
"""


def search_fts(
    conn: sqlite3.Connection,
    query: str,
    namespace: str,
    limit: int = 20,
) -> list[dict]:
    rows = conn.execute(_SEARCH_SQL, (_safe_query(query), namespace, limit)).fetchall()
    return [dict(r) for r in rows]


async def search_fts_async(
    db: aiosqlite.Connection,
    query: str,
    namespace: str,
    limit: int = 20,
) -> list[dict]:
    async with db.execute(_SEARCH_SQL, (_safe_query(query), namespace, limit)) as cur:
        rows = await cur.fetchall()
        col_names = [d[0] for d in cur.description]
    return [dict(zip(col_names, row)) for row in rows]
