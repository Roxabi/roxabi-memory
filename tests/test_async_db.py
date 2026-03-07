"""Tests for roxabi_memory.async_db — AsyncMemoryDB (S2)."""
from __future__ import annotations

import asyncio
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
