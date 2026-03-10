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
# init
# ---------------------------------------------------------------------------


def test_init_creates_vault(tmp_path) -> None:
    vault_home = tmp_path / "vault"
    db = vault_home / "vault.db"
    result = runner.invoke(app, ["--db", str(db), "init"])

    assert result.exit_code == 0
    assert db.exists()
    assert (vault_home / "config").is_dir()
    assert (vault_home / "content").is_dir()
    assert (vault_home / "ideas").is_dir()
    assert (vault_home / "learnings").is_dir()
    assert (vault_home / "backup").is_dir()


def test_init_existing_vault(db_path: str) -> None:
    result = runner.invoke(app, ["--db", db_path, "init"])

    assert result.exit_code == 0
    assert "already exists" in result.output.lower()


def test_init_json(tmp_path) -> None:
    vault_home = tmp_path / "vault"
    db = vault_home / "vault.db"
    result = runner.invoke(app, ["--db", str(db), "--json", "init"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "initialized"
    assert data["entries"] == 0


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


def test_search_with_limit(db_path: str) -> None:
    result = runner.invoke(
        app, ["--db", db_path, "--json", "search", "entry", "--limit", "1"]
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1


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


def test_put_with_type(db_path: str) -> None:
    result = runner.invoke(
        app,
        ["--db", db_path, "put", "my idea", "--type", "idea", "--category", "ideas"],
    )

    assert result.exit_code == 0

    with MemoryDB(db_path) as db:
        entries = db.list_entries(category="ideas")
    assert len(entries) == 1
    assert entries[0].type == "idea"


def test_put_with_metadata(db_path: str) -> None:
    result = runner.invoke(
        app,
        [
            "--db",
            db_path,
            "put",
            "with meta",
            "--metadata",
            '{"source": "test"}',
        ],
    )

    assert result.exit_code == 0

    with MemoryDB(db_path) as db:
        entries = db.list_entries()
    last = entries[-1]
    assert json.loads(last.metadata) == {"source": "test"}


def test_put_invalid_metadata(db_path: str) -> None:
    result = runner.invoke(
        app, ["--db", db_path, "put", "bad meta", "--metadata", "not json"]
    )

    assert result.exit_code == 1


def test_put_json_output(db_path: str) -> None:
    result = runner.invoke(app, ["--db", db_path, "--json", "put", "json out"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["content"] == "json out"


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


def test_export_with_category(db_path: str) -> None:
    result = runner.invoke(app, ["--db", db_path, "export", "--category", "notes"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2
    assert all(e["category"] == "notes" for e in data)


def test_export_to_file(db_path: str, tmp_path) -> None:
    out_file = tmp_path / "export.json"
    result = runner.invoke(app, ["--db", db_path, "export", "-o", str(out_file)])

    assert result.exit_code == 0
    data = json.loads(out_file.read_text())
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


def test_default_db_path(tmp_path, monkeypatch) -> None:
    """When no --db flag and no RMEM_DB, ROXABI_VAULT_HOME is used as default."""
    vault_home = tmp_path / ".roxabi-vault"
    monkeypatch.setenv("ROXABI_VAULT_HOME", str(vault_home))
    # init creates the vault at the default path
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert (vault_home / "vault.db").exists()
