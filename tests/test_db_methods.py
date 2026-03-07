"""Tests for new MemoryDB methods: get_entry, delete_entry, list_entries, get_stats."""

import pytest

from roxabi_memory.db import MemoryDB


@pytest.fixture
def db(tmp_path):
    d = MemoryDB(tmp_path / "test.db")
    d.connect()
    yield d
    d.close()


# ---------------------------------------------------------------------------
# get_entry
# ---------------------------------------------------------------------------


def test_get_entry_exists(db: MemoryDB) -> None:
    # Arrange
    saved = db.save_entry(
        "hello world", title="Greeting", category="notes", namespace="vault"
    )

    # Act
    result = db.get_entry(saved.id)

    # Assert
    assert result is not None
    assert result.id == saved.id
    assert result.content == "hello world"
    assert result.title == "Greeting"
    assert result.category == "notes"
    assert result.namespace == "vault"


def test_get_entry_not_found(db: MemoryDB) -> None:
    # Arrange — no entries saved

    # Act
    result = db.get_entry(999)

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# delete_entry
# ---------------------------------------------------------------------------


def test_delete_entry_exists(db: MemoryDB) -> None:
    # Arrange
    saved = db.save_entry("entry to delete")

    # Act
    deleted = db.delete_entry(saved.id)

    # Assert
    assert deleted is True
    assert db.get_entry(saved.id) is None


def test_delete_entry_not_found(db: MemoryDB) -> None:
    # Arrange — no entries saved

    # Act
    result = db.delete_entry(999)

    # Assert
    assert result is False


# ---------------------------------------------------------------------------
# list_entries
# ---------------------------------------------------------------------------


def test_list_entries_all(db: MemoryDB) -> None:
    # Arrange
    db.save_entry("entry one")
    db.save_entry("entry two")
    db.save_entry("entry three")

    # Act
    results = db.list_entries()

    # Assert
    assert len(results) == 3


def test_list_entries_filter_namespace(db: MemoryDB) -> None:
    # Arrange
    db.save_entry("vault entry", namespace="vault")
    db.save_entry("lyra entry", namespace="lyra")
    db.save_entry("another vault entry", namespace="vault")

    # Act
    results = db.list_entries(namespace="vault")

    # Assert
    assert len(results) == 2
    assert all(e.namespace == "vault" for e in results)


def test_list_entries_filter_category(db: MemoryDB) -> None:
    # Arrange
    db.save_entry("a note", category="notes")
    db.save_entry("a log", category="logs")
    db.save_entry("another note", category="notes")

    # Act
    results = db.list_entries(category="notes")

    # Assert
    assert len(results) == 2
    assert all(e.category == "notes" for e in results)


def test_list_entries_pagination(db: MemoryDB) -> None:
    # Arrange — save 5 entries so IDs are predictable in order
    for i in range(1, 6):
        db.save_entry(f"entry {i}")

    # Act — limit=2, offset=1 skips the first entry and returns the next 2
    results = db.list_entries(limit=2, offset=1)

    # Assert
    assert len(results) == 2


def test_list_entries_no_limit(db: MemoryDB) -> None:
    # Arrange
    for i in range(3):
        db.save_entry(f"entry {i}")

    # Act
    results = db.list_entries(limit=None)

    # Assert
    assert len(results) == 3


def test_list_entries_offset_without_limit_raises(db: MemoryDB) -> None:
    # Arrange
    db.save_entry("entry")

    # Act / Assert — offset without limit is invalid
    with pytest.raises(ValueError, match="offset requires limit"):
        db.list_entries(limit=None, offset=5)


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


def test_get_stats(db: MemoryDB) -> None:
    # Arrange
    db.save_entry("vault note", namespace="vault", category="notes")
    db.save_entry("lyra log", namespace="lyra", category="logs")
    db.save_entry("vault log", namespace="vault", category="logs")

    # Act
    stats = db.get_stats()

    # Assert
    assert stats["count"] == 3
    assert set(stats["namespaces"]) == {"vault", "lyra"}
    assert set(stats["categories"]) == {"notes", "logs"}
