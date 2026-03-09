"""Tests for roxabi_memory.search — hybrid search + RRF (S3 Slice 2)."""

from __future__ import annotations

import struct

import aiosqlite

from roxabi_memory.schema import MIGRATIONS, SCHEMA_V1_SQL
from roxabi_memory.search import _rrf_merge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _float32_blob(values: list[float]) -> bytes:
    return struct.pack(f"{len(values)}f", *values)


async def _setup_db(path, load_vec: bool = True):
    """Create a test DB with schema + migrations + sqlite-vec."""
    db = await aiosqlite.connect(str(path))
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db._execute(db._conn.executescript, SCHEMA_V1_SQL)
    for v in sorted(MIGRATIONS):
        for stmt in MIGRATIONS[v]:
            await db.execute(stmt)
    await db.execute(f"PRAGMA user_version = {max(MIGRATIONS)}")
    await db.commit()

    if load_vec:
        import sqlite_vec

        await db._execute(sqlite_vec.load, db._conn)

    return db


# ---------------------------------------------------------------------------
# T5: _rrf_merge with known inputs
# ---------------------------------------------------------------------------


def test_rrf_merge_ranks_dual_presence_higher():
    bm25 = [{"id": 1}, {"id": 2}, {"id": 3}]
    cosine = [{"id": 2}, {"id": 4}, {"id": 1}]
    merged = _rrf_merge(bm25, cosine, k=60)
    ids = [r["id"] for r in merged]
    # id=2: rank 2 in bm25 (1/62) + rank 1 in cosine (1/61) → highest
    # id=1: rank 1 in bm25 (1/61) + rank 3 in cosine (1/63) → second
    assert ids[0] == 2
    assert ids[1] == 1


def test_rrf_merge_single_list_entry():
    """Entry in only one list still appears in result."""
    bm25 = [{"id": 1}]
    cosine = [{"id": 2}]
    merged = _rrf_merge(bm25, cosine, k=60)
    ids = [r["id"] for r in merged]
    assert set(ids) == {1, 2}


def test_rrf_merge_empty_lists():
    merged = _rrf_merge([], [], k=60)
    assert merged == []


def test_rrf_merge_respects_k_parameter():
    """With very high k, all single-list entries have similar scores."""
    bm25 = [{"id": i} for i in range(5)]
    cosine = []
    merged = _rrf_merge(bm25, cosine, k=60)
    assert len(merged) == 5
    assert merged[0]["id"] == 0  # rank 1 → highest score


# ---------------------------------------------------------------------------
# T6: _cosine_search filters NULL embeddings
# ---------------------------------------------------------------------------


async def test_cosine_search_excludes_null_embeddings(tmp_path):
    from roxabi_memory.embeddings import Embedder
    from roxabi_memory.search import _cosine_search

    db = await _setup_db(tmp_path / "test.db")
    embedder = Embedder()
    emb = embedder.embed("hello world")

    # Entry with embedding
    await db.execute(
        "INSERT INTO entries (category, type, title, content, namespace, metadata, embedding)"
        " VALUES ('general', 'note', 'with emb', 'hello world', 'vault', '{}', ?)",
        (emb,),
    )
    # Entry without embedding
    await db.execute(
        "INSERT INTO entries (category, type, title, content, namespace, metadata)"
        " VALUES ('general', 'note', 'no emb', 'hello world too', 'vault', '{}')",
    )
    await db.commit()

    query_emb = embedder.embed("hello")
    results = await _cosine_search(db, query_emb, "vault", limit=10)

    await db.close()

    assert len(results) == 1
    assert results[0]["title"] == "with emb"


# ---------------------------------------------------------------------------
# T7: hybrid_search returns merged ranking
# ---------------------------------------------------------------------------


async def test_hybrid_search_returns_merged_ranking(tmp_path):
    from roxabi_memory.embeddings import Embedder
    from roxabi_memory.search import hybrid_search

    db = await _setup_db(tmp_path / "test.db")
    embedder = Embedder()

    # Entry 1: keyword match + embedding
    emb1 = embedder.embed("machine learning algorithms")
    await db.execute(
        "INSERT INTO entries (category, type, title, content, namespace, metadata, embedding)"
        " VALUES ('general', 'note', 'ML entry', 'machine learning algorithms', 'vault', '{}', ?)",
        (emb1,),
    )
    # Entry 2: keyword match only (no embedding)
    await db.execute(
        "INSERT INTO entries (category, type, title, content, namespace, metadata)"
        " VALUES ('general', 'note', 'ML basics', 'machine learning basics', 'vault', '{}')",
    )
    # Entry 3: embedding only (different keywords but semantically similar)
    emb3 = embedder.embed("neural network training")
    await db.execute(
        "INSERT INTO entries (category, type, title, content, namespace, metadata, embedding)"
        " VALUES ('general', 'note', 'NN entry', 'neural network training', 'vault', '{}', ?)",
        (emb3,),
    )
    await db.commit()

    results = await hybrid_search(db, embedder, "machine learning", "vault", limit=5)
    await db.close()

    # Entry 1 should rank highest (both BM25 + cosine match)
    assert results[0]["title"] == "ML entry"
    # Entry 2 (BM25-only) should still be present
    assert any(r["title"] == "ML basics" for r in results)


async def test_hybrid_search_respects_limit(tmp_path):
    from roxabi_memory.embeddings import Embedder
    from roxabi_memory.search import hybrid_search

    db = await _setup_db(tmp_path / "test.db")
    embedder = Embedder()

    for i in range(10):
        emb = embedder.embed(f"test entry number {i}")
        await db.execute(
            "INSERT INTO entries (category, type, title, content, namespace, metadata, embedding)"
            " VALUES ('general', 'note', ?, ?, 'vault', '{}', ?)",
            (f"entry {i}", f"test entry number {i}", emb),
        )
    await db.commit()

    results = await hybrid_search(db, embedder, "test entry", "vault", limit=3)
    await db.close()

    assert len(results) == 3
