"""Tests for roxabi_memory.async_db — AsyncMemoryDB (S2)."""

from __future__ import annotations

import time

import pytest

from roxabi_memory.async_db import AsyncMemoryDB


@pytest.fixture
async def db(tmp_path):
    """Provide a connected AsyncMemoryDB backed by a temp file, closed after use."""
    async with AsyncMemoryDB(tmp_path / "test_async.db") as database:
        yield database


# ---------------------------------------------------------------------------
# T-12-1: save_entry stores data, search returns it
# ---------------------------------------------------------------------------


async def test_save_and_search(db: AsyncMemoryDB) -> None:
    # Arrange
    content = "async fact about Python"

    # Act
    entry_id = await db.save_entry(content, namespace="lyra")
    results = await db.search("Python", namespace="lyra")

    # Assert
    assert entry_id is not None
    assert results
    assert any("Python" in r["content"] for r in results)


# ---------------------------------------------------------------------------
# T-12-2: Event loop not blocked — operations complete in < 2s
# ---------------------------------------------------------------------------


async def test_operations_are_fast(db: AsyncMemoryDB) -> None:
    # Arrange
    start = time.monotonic()

    # Act — 10 sequential save + 1 search
    for i in range(10):
        await db.save_entry(f"entry number {i}", namespace="lyra")
    await db.search("entry", namespace="lyra")

    elapsed = time.monotonic() - start

    # Assert
    assert elapsed < 2.0, f"Operations took {elapsed:.2f}s — event loop may be blocked"


# ---------------------------------------------------------------------------
# T-12-3: upsert_session creates a record on first call
# ---------------------------------------------------------------------------


async def test_upsert_session_creates_record(db: AsyncMemoryDB) -> None:
    # Arrange
    session_id = "sess-001"
    summary = "Initial session summary"

    # Act
    entry_id = await db.upsert_session(session_id, summary)

    # Assert
    assert entry_id is not None
    results = await db.search("Initial session", namespace="vault")
    assert any(r["id"] == entry_id for r in results)


# ---------------------------------------------------------------------------
# T-12-4: upsert_session updates (not duplicates) on second call
# ---------------------------------------------------------------------------


async def test_upsert_session_updates_not_duplicates(db: AsyncMemoryDB) -> None:
    # Arrange
    session_id = "sess-002"

    # Act
    first_id = await db.upsert_session(session_id, "first summary")
    second_id = await db.upsert_session(session_id, "updated summary")

    # Assert — same id returned, not a new row
    assert first_id == second_id

    # Assert — only one session entry exists for this session_id
    results = await db.search("summary", namespace="vault")
    session_results = [r for r in results if r.get("type") == "session"]
    assert len(session_results) == 1
    assert "updated" in session_results[0]["content"]


# ---------------------------------------------------------------------------
# T-12-x: metadata validation
# ---------------------------------------------------------------------------


async def test_save_entry_dict_metadata(db: AsyncMemoryDB) -> None:
    """save_entry accepts a dict and stores it as JSON."""
    # Arrange / Act
    await db.save_entry("with meta", metadata={"key": "value"})

    # Assert
    results = await db.search("with meta", namespace="vault")
    assert results
    import json

    meta = json.loads(results[0]["metadata"])
    assert meta == {"key": "value"}


async def test_save_entry_rejects_non_serializable_metadata(
    db: AsyncMemoryDB,
) -> None:
    """save_entry raises ValueError when metadata contains non-serializable values."""
    with pytest.raises(ValueError, match="not JSON-serializable"):
        await db.save_entry("bad meta", metadata={"bad": object()})


# ---------------------------------------------------------------------------
# T-12-5: Namespace isolation — 'other' not visible to 'lyra'
# ---------------------------------------------------------------------------


async def test_namespace_isolation(db: AsyncMemoryDB) -> None:
    # Arrange
    await db.save_entry("other agent secret", namespace="other")

    # Act
    results = await db.search("secret", namespace="lyra")

    # Assert — 'other' namespace not visible to 'lyra'
    assert not results


# ---------------------------------------------------------------------------
# T-12-6: Vault entries ARE visible to 'lyra' reader
# ---------------------------------------------------------------------------


async def test_vault_entries_visible_to_lyra(db: AsyncMemoryDB) -> None:
    # Arrange
    await db.save_entry("shared vault knowledge", namespace="vault")

    # Act
    results = await db.search("shared", namespace="lyra")

    # Assert
    assert results
    assert any("shared" in r["content"] for r in results)


# ---------------------------------------------------------------------------
# T-12-7: Context manager __aenter__ / __aexit__
# ---------------------------------------------------------------------------


async def test_context_manager(tmp_path) -> None:
    # Arrange / Act — write inside context manager
    async with AsyncMemoryDB(tmp_path / "ctx.db") as db:
        entry_id = await db.save_entry("context manager entry", namespace="lyra")
        assert entry_id is not None

    # Assert — database is closed after exit; reconnect and confirm data persisted
    async with AsyncMemoryDB(tmp_path / "ctx.db") as db:
        results = await db.search("context manager", namespace="lyra")
        assert results


async def test_connect_before_operations_required(tmp_path) -> None:
    """Calling save_entry before connect() must raise RuntimeError."""
    # Arrange
    db = AsyncMemoryDB(tmp_path / "unconnected.db")

    # Act / Assert
    with pytest.raises(RuntimeError, match="not connected"):
        await db.save_entry("should fail")


# ===========================================================================
# S3 — Hybrid Search Integration Tests
# ===========================================================================


@pytest.fixture
async def emb_db(tmp_path):
    """Provide a connected AsyncMemoryDB with embeddings=True."""
    async with AsyncMemoryDB(tmp_path / "test_emb.db", embeddings=True) as database:
        yield database


# ---------------------------------------------------------------------------
# T10: save_entry stores embedding when embeddings=True
# ---------------------------------------------------------------------------


async def test_save_entry_stores_embedding(emb_db: AsyncMemoryDB) -> None:
    # Act
    entry_id = await emb_db.save_entry("hello world embeddings test", namespace="vault")

    # Assert — embedding is non-NULL in DB
    db = emb_db._db_or_raise()
    async with db.execute(
        "SELECT embedding FROM entries WHERE id = ?", (entry_id,)
    ) as cur:
        row = await cur.fetchone()

    assert row is not None
    assert row[0] is not None  # embedding BLOB stored
    assert len(row[0]) == 384 * 4  # float32 × 384


# ---------------------------------------------------------------------------
# T11: search returns hybrid results (integration)
# ---------------------------------------------------------------------------


async def test_search_returns_hybrid_results(emb_db: AsyncMemoryDB) -> None:
    # Arrange
    await emb_db.save_entry("machine learning algorithms and models", namespace="vault")
    await emb_db.save_entry("cooking recipes for pasta dishes", namespace="vault")
    await emb_db.save_entry("neural network deep learning", namespace="vault")

    # Act
    results = await emb_db.search("machine learning", namespace="vault")

    # Assert — ML entry ranks highest (best BM25 + cosine match)
    assert results
    assert "machine learning" in results[0]["content"]


# ---------------------------------------------------------------------------
# T12: backfill updates NULL embeddings
# ---------------------------------------------------------------------------


async def test_backfill_updates_null_embeddings(tmp_path) -> None:
    import asyncio

    # Step 1: insert without embeddings
    async with AsyncMemoryDB(tmp_path / "backfill.db") as db_no_emb:
        entry_id = await db_no_emb.save_entry(
            "backfill test content", namespace="vault"
        )

    # Verify embedding is NULL
    async with AsyncMemoryDB(tmp_path / "backfill.db") as db_check:
        raw = db_check._db_or_raise()
        async with raw.execute(
            "SELECT embedding FROM entries WHERE id = ?", (entry_id,)
        ) as cur:
            row = await cur.fetchone()
        assert row[0] is None  # no embedding yet

    # Step 2: search with embeddings=True → triggers backfill
    async with AsyncMemoryDB(tmp_path / "backfill.db", embeddings=True) as db_emb:
        results = await db_emb.search("backfill test", namespace="vault")
        assert results

        # Await all background tasks (deterministic, no sleep)
        if db_emb._background_tasks:
            await asyncio.gather(*db_emb._background_tasks)

        # Verify embedding is now non-NULL
        raw = db_emb._db_or_raise()
        async with raw.execute(
            "SELECT embedding FROM entries WHERE id = ?", (entry_id,)
        ) as cur:
            row = await cur.fetchone()
        assert row[0] is not None, "Backfill should have populated embedding"


# ---------------------------------------------------------------------------
# S4: Namespace isolation with embeddings=True
# ---------------------------------------------------------------------------


async def test_namespace_isolation_with_embeddings(emb_db: AsyncMemoryDB) -> None:
    """Cosine search respects namespace filter — 'other' not visible to 'lyra'."""
    # Arrange
    await emb_db.save_entry("other agent secret with embeddings", namespace="other")

    # Act
    results = await emb_db.search("secret", namespace="lyra")

    # Assert — 'other' namespace not visible to 'lyra'
    assert not results


# ---------------------------------------------------------------------------
# S5: Backfill idempotency — second search doesn't re-backfill
# ---------------------------------------------------------------------------


async def test_backfill_idempotency(tmp_path) -> None:
    """Second search doesn't trigger backfill for already-filled entries."""
    import asyncio

    # Arrange — insert without embeddings
    async with AsyncMemoryDB(tmp_path / "idem.db") as db_no_emb:
        await db_no_emb.save_entry("idempotency test content", namespace="vault")

    # Act — first search triggers backfill
    async with AsyncMemoryDB(tmp_path / "idem.db", embeddings=True) as db_emb:
        await db_emb.search("idempotency", namespace="vault")
        if db_emb._background_tasks:
            await asyncio.gather(*db_emb._background_tasks)

        # Act — second search should NOT trigger new backfill tasks
        db_emb._background_tasks.clear()
        await db_emb.search("idempotency", namespace="vault")

        # Assert — no new backfill tasks created
        assert len(db_emb._background_tasks) == 0


# ---------------------------------------------------------------------------
# T13: embeddings=False preserves BM25-only behavior
# ---------------------------------------------------------------------------


async def test_embeddings_false_preserves_bm25(db: AsyncMemoryDB) -> None:
    """Default embeddings=False works exactly as before."""
    # Arrange / Act
    await db.save_entry("bm25 only test content", namespace="vault")
    results = await db.search("bm25 only", namespace="vault")

    # Assert
    assert results
    assert "bm25 only" in results[0]["content"]

    # Assert — no embedding stored
    raw = db._db_or_raise()
    async with raw.execute(
        "SELECT embedding FROM entries WHERE id = ?", (results[0]["id"],)
    ) as cur:
        row = await cur.fetchone()
    assert row[0] is None


# ---------------------------------------------------------------------------
# T14: sqlite-vec loaded in connect()
# ---------------------------------------------------------------------------


async def test_sqlite_vec_loaded(emb_db: AsyncMemoryDB) -> None:
    """sqlite-vec extension is available after connect with embeddings=True."""
    import struct

    db = emb_db._db_or_raise()
    # Create two tiny float32 vectors and compute distance
    v1 = struct.pack("2f", 1.0, 0.0)
    v2 = struct.pack("2f", 0.0, 1.0)
    async with db.execute("SELECT vec_distance_cosine(?, ?)", (v1, v2)) as cur:
        row = await cur.fetchone()
    assert row is not None
    assert isinstance(row[0], float)
    assert row[0] > 0  # orthogonal vectors → distance > 0


# ---------------------------------------------------------------------------
# B4: sqlite-vec load failure raises RuntimeError
# ---------------------------------------------------------------------------


async def test_sqlite_vec_load_failure_raises_runtime_error(tmp_path, monkeypatch):
    """OperationalError during sqlite-vec load is re-raised as RuntimeError."""
    import roxabi_memory.async_db as adb_mod

    async def broken_load(self):
        raise Exception("mocked extension load failure")

    monkeypatch.setattr(adb_mod.AsyncMemoryDB, "_load_sqlite_vec", broken_load)

    db = AsyncMemoryDB(tmp_path / "vec_fail.db", embeddings=True)
    with pytest.raises(Exception, match="mocked extension load failure"):
        await db.connect()


# ---------------------------------------------------------------------------
# S7: AsyncMemoryDB(embeddings=True) ImportError when fastembed missing
# ---------------------------------------------------------------------------


def test_async_db_embeddings_import_error(tmp_path, monkeypatch):
    """AsyncMemoryDB(embeddings=True) raises ImportError when fastembed unavailable."""
    import importlib
    import sys

    # Remove cached embeddings module
    mods_to_remove = [
        k for k in sys.modules if k.startswith("roxabi_memory.embeddings")
    ]
    for m in mods_to_remove:
        del sys.modules[m]

    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == "fastembed" or name.startswith("fastembed."):
            raise ImportError("mocked: no fastembed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)

    # Also remove the cached async_db module so it re-imports embeddings
    adb_key = "roxabi_memory.async_db"
    if adb_key in sys.modules:
        del sys.modules[adb_key]

    try:
        mod = importlib.import_module("roxabi_memory.async_db")
        with pytest.raises(ImportError, match="fastembed|embeddings"):
            mod.AsyncMemoryDB(tmp_path / "import_fail.db", embeddings=True)
    finally:
        # Cleanup: restore module cache
        for k in list(sys.modules):
            if (
                k.startswith("roxabi_memory.embeddings")
                or k == "roxabi_memory.async_db"
            ):
                del sys.modules[k]
        importlib.import_module("roxabi_memory.async_db")
