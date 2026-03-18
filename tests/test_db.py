"""Tests for roxabi_vault.db — MemoryDB and MemoryEntry."""

import pytest

from roxabi_vault.db import MemoryDB


@pytest.fixture
def db(tmp_path):
    d = MemoryDB(tmp_path / "test.db")
    d.connect()
    yield d
    d.close()


def test_save_and_retrieve(db: MemoryDB) -> None:
    # Arrange / Act
    entry = db.save_entry("Mickael prefers Python", namespace="lyra")

    # Assert
    assert entry.id is not None
    assert entry.namespace == "lyra"
    assert "Python" in entry.content


def test_search_own_namespace(db: MemoryDB) -> None:
    # Arrange
    db.save_entry("lyra-specific fact", namespace="lyra")

    # Act
    results = db.search_fts("lyra-specific", namespace="lyra")

    # Assert
    assert results
    assert any("lyra-specific" in r.content for r in results)


def test_namespace_isolation(db: MemoryDB) -> None:
    """Entries in a foreign namespace must not appear when querying a different namespace."""
    # Arrange
    db.save_entry("other agent secret", namespace="other_agent")

    # Act
    results = db.search_fts("secret", namespace="lyra")

    # Assert — 'other_agent' namespace not visible to 'lyra'
    assert not results


def test_vault_namespace_visible_to_all(db: MemoryDB) -> None:
    """vault entries must be returned for any namespace query."""
    # Arrange
    db.save_entry("shared knowledge", namespace="vault")

    # Act
    results = db.search_fts("shared", namespace="lyra")

    # Assert
    assert results


def test_context_manager(tmp_path) -> None:
    # Arrange / Act
    with MemoryDB(tmp_path / "ctx.db") as db:
        db.save_entry("context manager test")

    # Assert — reconnecting to the same file should find the persisted row
    with MemoryDB(tmp_path / "ctx.db") as db:
        results = db.search_fts("context manager")
        assert results


def test_fts_query_sanitisation(db: MemoryDB) -> None:
    """Malformed FTS5 query tokens must not raise an exception."""
    # Arrange
    db.save_entry("test content", namespace="lyra")

    # Act / Assert — none of these should raise
    db.search_fts("test*", namespace="lyra")
    db.search_fts('te"st', namespace="lyra")
    db.search_fts("test^2", namespace="lyra")


def test_save_entry_defaults(db: MemoryDB) -> None:
    """save_entry with only content uses expected defaults."""
    # Act
    entry = db.save_entry("minimal entry")

    # Assert
    assert entry.category == "general"
    assert entry.type == "note"
    assert entry.namespace == "vault"
    assert entry.metadata == "{}"


def test_save_entry_dict_metadata(db: MemoryDB) -> None:
    """save_entry accepts a dict and stores it as JSON."""
    # Arrange / Act
    entry = db.save_entry("with meta", metadata={"key": "value", "n": 42})

    # Assert
    assert entry.metadata == '{"key": "value", "n": 42}'


def test_save_entry_rejects_non_serializable_metadata(db: MemoryDB) -> None:
    """save_entry raises ValueError when metadata contains non-serializable values."""
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="not JSON-serializable"):
        db.save_entry("bad meta", metadata={"bad": object()})


def test_not_connected_raises(tmp_path) -> None:
    """Calling save_entry before connect() must raise RuntimeError."""
    # Arrange
    db = MemoryDB(tmp_path / "unconnected.db")

    # Act / Assert
    with pytest.raises(RuntimeError, match="not connected"):
        db.save_entry("this should fail")
