"""CLI for roxabi-vault — rmem command."""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from .db import MemoryDB

app = typer.Typer(help="roxabi-vault CLI — manage memory entries.")

console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def _default_vault_home() -> Path:
    return Path(os.environ.get("ROXABI_VAULT_HOME", str(Path.home() / ".roxabi-vault")))


def _default_db_path() -> Path:
    return _default_vault_home() / "vault.db"


# ---------------------------------------------------------------------------
# Shared state via callback
# ---------------------------------------------------------------------------


class _State:
    db_path: Path | None = None
    as_json: bool = False


state = _State()


@app.callback()
def main(
    db: Annotated[
        Optional[str],
        typer.Option(
            "--db", envvar="VAULT_DB", help="Path to the SQLite database file."
        ),
    ] = None,
    as_json: Annotated[
        bool, typer.Option("--json", is_flag=True, help="Output as JSON.")
    ] = False,
) -> None:
    """roxabi-vault — a local SQLite memory store."""
    state.db_path = Path(db) if db else _default_db_path()
    state.as_json = as_json


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@app.command("init")
def init_vault() -> None:
    """Initialize the vault: create directories and database."""
    vault_home = state.db_path.parent

    if state.db_path.exists():
        with MemoryDB(state.db_path) as db:
            data = db.get_stats()
        if state.as_json:
            typer.echo(
                json.dumps(
                    {
                        "vault_home": str(vault_home),
                        "db_path": str(state.db_path),
                        "entries": data["count"],
                        "status": "exists",
                    },
                    indent=2,
                )
            )
            return
        console.print(f"Vault already exists at {vault_home}")
        console.print(f"  Entries: {data['count']}")
        return

    vault_home.mkdir(parents=True, exist_ok=True)
    vault_home.chmod(0o700)
    for sub in ("config", "content", "ideas", "learnings", "backup"):
        (vault_home / sub).mkdir(exist_ok=True)

    with MemoryDB(state.db_path) as db:
        data = db.get_stats()

    if state.as_json:
        typer.echo(
            json.dumps(
                {
                    "vault_home": str(vault_home),
                    "db_path": str(state.db_path),
                    "entries": data["count"],
                    "status": "initialized",
                },
                indent=2,
            )
        )
        return

    console.print("[bold green]Vault initialized[/bold green]")
    console.print(f"  Location:    {vault_home}")
    console.print(f"  Database:    {state.db_path.name}")
    console.print("  WAL mode:    enabled")
    console.print("  Directories: config/, content/, ideas/, learnings/, backup/")
    console.print("  Status:      ready")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@app.command("list")
def list_entries(
    namespace: Annotated[
        Optional[str], typer.Option("--namespace", help="Filter by namespace.")
    ] = None,
    category: Annotated[
        Optional[str], typer.Option("--category", help="Filter by category.")
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", help="Maximum number of results.")
    ] = 50,
    offset: Annotated[
        int, typer.Option("--offset", help="Number of entries to skip.")
    ] = 0,
) -> None:
    """List memory entries."""
    with MemoryDB(state.db_path) as db:
        entries = db.list_entries(
            namespace=namespace, category=category, limit=limit, offset=offset
        )

    if state.as_json:
        typer.echo(json.dumps([dataclasses.asdict(e) for e in entries], indent=2))
        return

    table = Table(show_header=True, header_style="bold")
    for col in ("id", "title", "namespace", "category", "type", "created_at"):
        table.add_column(col)
    for e in entries:
        table.add_row(str(e.id), e.title, e.namespace, e.category, e.type, e.created_at)
    console.print(table)


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@app.command("search")
def search_entries(
    query: Annotated[str, typer.Argument(help="Full-text search query.")],
    namespace: Annotated[
        Optional[str],
        typer.Option("--namespace", help="Restrict search to namespace (+ vault)."),
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", help="Maximum number of results.")
    ] = 20,
) -> None:
    """Full-text search over memory entries."""
    with MemoryDB(state.db_path) as db:
        entries = db.search_fts(query, namespace=namespace, limit=limit)

    if state.as_json:
        typer.echo(json.dumps([dataclasses.asdict(e) for e in entries], indent=2))
        return

    table = Table(show_header=True, header_style="bold")
    for col in ("id", "title", "namespace", "category", "type", "created_at"):
        table.add_column(col)
    for e in entries:
        table.add_row(str(e.id), e.title, e.namespace, e.category, e.type, e.created_at)
    console.print(table)


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


@app.command("get")
def get_entry(
    id: Annotated[str, typer.Argument(help="Entry ID.")],
) -> None:
    """Get a single memory entry by ID."""
    try:
        entry_id = int(id)
    except ValueError:
        err_console.print(f"Invalid ID: {id!r} is not an integer.")
        raise typer.Exit(code=1)
    with MemoryDB(state.db_path) as db:
        entry = db.get_entry(entry_id)

    if entry is None:
        err_console.print(f"Entry {entry_id} not found.")
        raise typer.Exit(code=1)

    if state.as_json:
        typer.echo(json.dumps(dataclasses.asdict(entry), indent=2))
        return

    d = dataclasses.asdict(entry)
    table = Table(show_header=False)
    table.add_column("field", style="bold")
    table.add_column("value")
    for key, value in d.items():
        table.add_row(key, str(value))
    console.print(table)


# ---------------------------------------------------------------------------
# put
# ---------------------------------------------------------------------------


@app.command("put")
def put_entry(
    content: Annotated[str, typer.Argument(help="Content of the memory entry.")],
    title: Annotated[
        Optional[str],
        typer.Option("--title", help="Title (defaults to first 80 chars of content)."),
    ] = None,
    category: Annotated[
        str, typer.Option("--category", help="Category tag.")
    ] = "general",
    type: Annotated[str, typer.Option("--type", help="Entry type.")] = "note",
    namespace: Annotated[
        str, typer.Option("--namespace", help="Namespace for the entry.")
    ] = "vault",
    metadata: Annotated[
        Optional[str],
        typer.Option("--metadata", help="JSON metadata string."),
    ] = None,
) -> None:
    """Save a new memory entry."""
    meta_dict = None
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError as exc:
            err_console.print(f"Invalid JSON metadata: {exc}")
            raise typer.Exit(code=1)

    with MemoryDB(state.db_path) as db:
        entry = db.save_entry(
            content,
            type=type,
            title=title or "",
            category=category,
            namespace=namespace,
            metadata=meta_dict,
        )

    if state.as_json:
        typer.echo(json.dumps(dataclasses.asdict(entry), indent=2))
        return

    typer.echo(f"Saved entry {entry.id}: {entry.title!r}")


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@app.command("delete")
def delete_entry(
    id: Annotated[str, typer.Argument(help="Entry ID to delete.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", is_flag=True, help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Delete a memory entry by ID."""
    try:
        entry_id = int(id)
    except ValueError:
        err_console.print(f"Invalid ID: {id!r} is not an integer.")
        raise typer.Exit(code=1)
    if not yes:
        typer.confirm(f"Delete entry {entry_id}?", abort=True)
    with MemoryDB(state.db_path) as db:
        deleted = db.delete_entry(entry_id)
    if deleted:
        typer.echo(f"Deleted entry {entry_id}.")
    else:
        err_console.print(f"Entry {entry_id} not found.")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


@app.command("stats")
def stats() -> None:
    """Show database statistics."""
    db_path = state.db_path
    with MemoryDB(db_path) as db:
        data = db.get_stats()

    try:
        size_bytes = os.path.getsize(db_path)
    except OSError:
        size_bytes = 0

    if state.as_json:
        data["db_path"] = str(db_path)
        data["size_bytes"] = size_bytes
        typer.echo(json.dumps(data, indent=2))
        return

    console.print(f"[bold]DB path:[/bold] {db_path}")
    console.print(f"[bold]Size:[/bold] {size_bytes:,} bytes")
    console.print(f"[bold]Total entries:[/bold] {data['count']}")
    console.print(
        f"[bold]Namespaces:[/bold] {', '.join(data['namespaces']) or '(none)'}"
    )
    console.print(
        f"[bold]Categories:[/bold] {', '.join(data['categories']) or '(none)'}"
    )


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@app.command("export")
def export_entries(
    category: Annotated[
        Optional[str], typer.Option("--category", help="Filter by category.")
    ] = None,
    namespace: Annotated[
        Optional[str], typer.Option("--namespace", help="Filter by namespace.")
    ] = None,
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Write to file instead of stdout."),
    ] = None,
) -> None:
    """Export entries as a JSON array."""
    with MemoryDB(state.db_path) as db:
        entries = db.list_entries(limit=None, category=category, namespace=namespace)
    data = json.dumps([dataclasses.asdict(e) for e in entries], indent=2)
    if output:
        Path(output).write_text(data)
        console.print(f"Exported {len(entries)} entries to {output}")
    else:
        typer.echo(data)
