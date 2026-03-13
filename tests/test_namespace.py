"""Tests for roxabi_vault.namespace — NamespacedReader + NamespacedWriter (S2)."""

from __future__ import annotations

import pytest

from roxabi_vault.async_db import AsyncMemoryDB
from roxabi_vault.namespace import NamespacedReader, NamespacedWriter


@pytest.fixture
async def db(tmp_path):
    """Provide a connected AsyncMemoryDB backed by a temp file."""
    async with AsyncMemoryDB(tmp_path / "test_ns.db") as database:
        yield database


# ---------------------------------------------------------------------------
# T-13-1: NamespacedReader.search returns own namespace entries
# ---------------------------------------------------------------------------


async def test_reader_returns_own_namespace(db: AsyncMemoryDB) -> None:
    # Arrange
    writer = NamespacedWriter(db, "lyra")
    await writer.save("lyra specific knowledge", type="note")
    reader = NamespacedReader(db, "lyra")

    # Act
    results = await reader.search("lyra specific")

    # Assert
    assert results
    assert any("lyra specific" in r["content"] for r in results)


# ---------------------------------------------------------------------------
# T-13-2: NamespacedReader.search returns vault namespace entries
# ---------------------------------------------------------------------------


async def test_reader_returns_vault_entries(db: AsyncMemoryDB) -> None:
    # Arrange — save a vault entry directly through the DB
    await db.save_entry("vault shared fact", namespace="vault")
    reader = NamespacedReader(db, "lyra")

    # Act
    results = await reader.search("vault shared")

    # Assert
    assert results
    assert any("vault shared" in r["content"] for r in results)


# ---------------------------------------------------------------------------
# T-13-3: NamespacedReader.search does NOT return other namespace entries
# ---------------------------------------------------------------------------


async def test_reader_excludes_other_namespaces(db: AsyncMemoryDB) -> None:
    # Arrange — save an entry in an unrelated namespace
    other_writer = NamespacedWriter(db, "other_agent")
    await other_writer.save("other agent private data")
    reader = NamespacedReader(db, "lyra")

    # Act
    results = await reader.search("private data")

    # Assert
    assert not results


# ---------------------------------------------------------------------------
# T-13-4: NamespacedWriter.save stores with correct namespace
# ---------------------------------------------------------------------------


async def test_writer_stores_with_correct_namespace(db: AsyncMemoryDB) -> None:
    # Arrange
    writer = NamespacedWriter(db, "my_agent")

    # Act
    entry_id = await writer.save("my agent content", type="note", title="Test Entry")

    # Assert — entry is findable via db.search with matching namespace
    results = await db.search("my agent content", namespace="my_agent")
    assert results
    assert results[0]["id"] == entry_id
    assert results[0]["namespace"] == "my_agent"


# ---------------------------------------------------------------------------
# T-13-5: Two writers in different namespaces don't bleed
# ---------------------------------------------------------------------------


async def test_two_writers_no_bleeding(db: AsyncMemoryDB) -> None:
    # Arrange
    writer_a = NamespacedWriter(db, "agent_a")
    writer_b = NamespacedWriter(db, "agent_b")
    reader_a = NamespacedReader(db, "agent_a")
    reader_b = NamespacedReader(db, "agent_b")

    # Act — each writer saves unique content
    await writer_a.save("agent_a exclusive information")
    await writer_b.save("agent_b exclusive information")

    results_a = await reader_a.search("exclusive information")
    results_b = await reader_b.search("exclusive information")

    # Assert — each reader sees only their own namespace
    assert results_a
    assert results_b

    namespaces_seen_by_a = {r["namespace"] for r in results_a}
    namespaces_seen_by_b = {r["namespace"] for r in results_b}

    # agent_a reader must not see agent_b's entries (and vice versa)
    assert "agent_b" not in namespaces_seen_by_a
    assert "agent_a" not in namespaces_seen_by_b
