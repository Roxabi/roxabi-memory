"""Integration tests for the roxabi-memory CLI (roxabi_memory.cli)."""

import json

import pytest
from typer.testing import CliRunner

from roxabi_memory.cli import app
from roxabi_memory.db import MemoryDB

runner = CliRunner()


@pytest.fixture
def db_path(tmp_path):
    """Create a seeded test database and return its path as string."""
    path = tmp_path / "test.db"
    with MemoryDB(path) as db:
        db.save_entry("first entry", title="First", category="notes", namespace="vault")
        db.save_entry("second entry", title="Second", category="logs", namespace="lyra")
        db.save_entry("third entry", title="Third", category="notes", namespace="vault")
    return str(path)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_list_default(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "list"])

    # Assert
    assert result.exit_code == 0
    assert "First" in result.output
    assert "Second" in result.output
    assert "Third" in result.output


def test_list_namespace_filter(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "list", "--namespace", "vault"])

    # Assert
    assert result.exit_code == 0
    assert "First" in result.output
    assert "Third" in result.output
    assert "Second" not in result.output


def test_list_category_filter(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "list", "--category", "notes"])

    # Assert
    assert result.exit_code == 0
    assert "First" in result.output
    assert "Third" in result.output
    assert "Second" not in result.output


def test_list_pagination(db_path: str) -> None:
    # Arrange / Act — only 1 entry, starting from offset 1
    result = runner.invoke(
        app, ["--db", db_path, "list", "--limit", "1", "--offset", "1"]
    )

    # Assert
    assert result.exit_code == 0
    # Exactly one entry must appear; the output must not contain all three titles simultaneously
    titles_found = sum(1 for t in ("First", "Second", "Third") if t in result.output)
    assert titles_found == 1


def test_list_json(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "--json", "list"])

    # Assert
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 3


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def test_search(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "search", "first"])

    # Assert
    assert result.exit_code == 0
    assert "First" in result.output


def test_search_namespace(db_path: str) -> None:
    # Arrange / Act — lyra namespace sees its own entries + vault entries
    result = runner.invoke(
        app, ["--db", db_path, "search", "entry", "--namespace", "lyra"]
    )

    # Assert
    assert result.exit_code == 0
    assert "Second" in result.output
    # vault entries are also visible to lyra (by design)
    assert "First" in result.output


def test_search_json(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "--json", "search", "entry"])

    # Assert
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_get_found(db_path: str) -> None:
    # Arrange / Act — entry id=1 is the first seeded entry
    result = runner.invoke(app, ["--db", db_path, "get", "1"])

    # Assert
    assert result.exit_code == 0
    assert "first entry" in result.output.lower()


def test_get_not_found(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "get", "999"])

    # Assert
    assert result.exit_code == 1


def test_get_invalid_id(db_path: str) -> None:
    # Arrange / Act — non-integer ID
    result = runner.invoke(app, ["--db", db_path, "get", "abc"])

    # Assert
    assert result.exit_code == 1
    assert "not an integer" in result.output.lower()


def test_get_json(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "--json", "get", "1"])

    # Assert
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert "content" in data


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


def test_stats(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "stats"])

    # Assert
    assert result.exit_code == 0
    assert "3" in result.output
    assert "vault" in result.output
    assert "lyra" in result.output
    assert "notes" in result.output
    assert "logs" in result.output


def test_stats_json(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "--json", "stats"])

    # Assert
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert "count" in data
    assert "namespaces" in data
    assert "categories" in data
    assert data["count"] == 3


# ---------------------------------------------------------------------------
# put
# ---------------------------------------------------------------------------


def test_put_minimal(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "put", "new content"])

    # Assert
    assert result.exit_code == 0
    # Output should mention the newly assigned ID (any integer)
    assert any(char.isdigit() for char in result.output)


def test_put_all_flags(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(
        app,
        [
            "--db",
            db_path,
            "put",
            "flagged content",
            "--title",
            "T",
            "--category",
            "C",
            "--namespace",
            "N",
        ],
    )

    # Assert
    assert result.exit_code == 0

    # Verify the entry was actually persisted with the correct fields
    with MemoryDB(db_path) as db:
        entries = db.list_entries(namespace="N", category="C")
    assert len(entries) == 1
    assert entries[0].title == "T"
    assert entries[0].content == "flagged content"
    assert entries[0].namespace == "N"
    assert entries[0].category == "C"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_with_yes(db_path: str) -> None:
    # Arrange / Act — use --yes to skip confirmation prompt
    result = runner.invoke(app, ["--db", db_path, "delete", "1", "--yes"])

    # Assert
    assert result.exit_code == 0
    with MemoryDB(db_path) as db:
        assert db.get_entry(1) is None


def test_delete_not_found(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "delete", "999", "--yes"])

    # Assert
    assert result.exit_code == 1


def test_delete_confirm_yes(db_path: str) -> None:
    # Arrange / Act — no --yes, simulate user typing "y"
    result = runner.invoke(app, ["--db", db_path, "delete", "1"], input="y\n")

    # Assert
    assert result.exit_code == 0
    with MemoryDB(db_path) as db:
        assert db.get_entry(1) is None


def test_delete_confirm_no(db_path: str) -> None:
    # Arrange / Act — no --yes, simulate user typing "n"
    result = runner.invoke(app, ["--db", db_path, "delete", "1"], input="n\n")

    # Assert — entry should still exist
    assert result.exit_code != 0
    with MemoryDB(db_path) as db:
        assert db.get_entry(1) is not None


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


def test_export(db_path: str) -> None:
    # Arrange / Act
    result = runner.invoke(app, ["--db", db_path, "export"])

    # Assert
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 3


# ---------------------------------------------------------------------------
# Global options
# ---------------------------------------------------------------------------


def test_db_env_var(db_path: str) -> None:
    # Arrange / Act — pass db path via environment variable instead of --db flag
    result = runner.invoke(app, ["list"], env={"RMEM_DB": db_path})

    # Assert
    assert result.exit_code == 0
    assert "First" in result.output


def test_no_db() -> None:
    # Arrange / Act — no --db flag and no RMEM_DB env var set
    result = runner.invoke(app, ["list"], env={})

    # Assert
    assert result.exit_code == 1
