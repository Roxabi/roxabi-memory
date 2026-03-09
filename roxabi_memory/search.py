"""Hybrid search — BM25 + cosine similarity via RRF merge."""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiosqlite

from .fts import search_fts_async

if TYPE_CHECKING:
    from .embeddings import Embedder

_COSINE_SQL = """
    SELECT e.id, e.category, e.type, e.title, e.content,
           e.namespace, e.metadata, e.created_at, e.updated_at,
           vec_distance_cosine(e.embedding, ?) AS distance
    FROM entries e
    WHERE e.embedding IS NOT NULL
      AND (e.namespace = ? OR e.namespace = 'vault')
    ORDER BY distance
    LIMIT ?
"""


async def _bm25_search(
    db: aiosqlite.Connection,
    query: str,
    namespace: str,
    limit: int,
) -> list[dict]:
    """BM25 keyword search — delegates to existing FTS5 implementation."""
    return await search_fts_async(db, query, namespace, limit)


async def _cosine_search(
    db: aiosqlite.Connection,
    query_embedding: bytes,
    namespace: str,
    limit: int,
) -> list[dict]:
    """Cosine similarity search via sqlite-vec. Excludes NULL embeddings."""
    async with db.execute(_COSINE_SQL, (query_embedding, namespace, limit)) as cur:
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
    # Strip 'distance' column — keep result schema consistent with BM25 results
    return [{k: v for k, v in zip(cols, r) if k != "distance"} for r in rows]


def _rrf_merge(
    bm25_results: list[dict],
    cosine_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion: score(d) = Σ 1/(k + rank_i(d)).

    rank_i is 1-based ordinal position in each list.
    Documents absent from a list contribute 0 for that list.
    """
    scores: dict[int, float] = {}
    docs: dict[int, dict] = {}

    for rank, doc in enumerate(bm25_results, 1):
        did = doc["id"]
        scores[did] = scores.get(did, 0.0) + 1.0 / (k + rank)
        docs[did] = doc

    for rank, doc in enumerate(cosine_results, 1):
        did = doc["id"]
        scores[did] = scores.get(did, 0.0) + 1.0 / (k + rank)
        docs[did] = doc

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [docs[did] for did, _ in ranked]


async def hybrid_search(
    db: aiosqlite.Connection,
    embedder: Embedder,
    query: str,
    namespace: str,
    limit: int = 5,
) -> list[dict]:
    """Run BM25 + cosine, merge via RRF, return top `limit` results."""
    fetch = limit * 2
    bm25 = await _bm25_search(db, query, namespace, fetch)
    query_emb = await embedder.embed_async(query)
    cosine = await _cosine_search(db, query_emb, namespace, fetch)
    merged = _rrf_merge(bm25, cosine, k=60)
    return merged[:limit]
