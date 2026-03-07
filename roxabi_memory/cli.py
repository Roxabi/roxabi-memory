"""CLI for roxabi-memory — rmem command."""

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

app = typer.Typer(help="roxabi-memory CLI — manage memory entries.")

console = Console()
err_console = Console(stderr=True)

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
            "--db", envvar="RMEM_DB", help="Path to the SQLite database file."
        ),
    ] = None,
    as_json: Annotated[
        bool, typer.Option("--json", is_flag=True, help="Output as JSON.")
    ] = False,
) -> None:
    """roxabi-memory — a local SQLite memory store."""
    if not db:
        err_console.print("Error: --db or RMEM_DB environment variable is required.")
        raise typer.Exit(code=1)
    state.db_path = Path(db)
    state.as_json = as_json


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
) -> None:
    """Full-text search over memory entries."""
    with MemoryDB(state.db_path) as db:
        entries = db.search_fts(query, namespace=namespace)

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
    id: Annotated[int, typer.Argument(help="Entry ID.")],
) -> None:
    """Get a single memory entry by ID."""
    with MemoryDB(state.db_path) as db:
        entry = db.get_entry(id)

    if entry is None:
        err_console.print(f"Entry {id} not found.")
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
    namespace: Annotated[
        str, typer.Option("--namespace", help="Namespace for the entry.")
    ] = "vault",
) -> None:
    """Save a new memory entry."""
    with MemoryDB(state.db_path) as db:
        entry = db.save_entry(
            content,
            type="note",
            title=title or "",
            category=category,
            namespace=namespace,
        )
    typer.echo(f"Saved entry {entry.id}: {entry.title!r}")


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@app.command("delete")
def delete_entry(
    id: Annotated[int, typer.Argument(help="Entry ID to delete.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", is_flag=True, help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Delete a memory entry by ID."""
    if not yes:
        typer.confirm(f"Delete entry {id}?", abort=True)
    with MemoryDB(state.db_path) as db:
        deleted = db.delete_entry(id)
    if deleted:
        typer.echo(f"Deleted entry {id}.")
    else:
        err_console.print(f"Entry {id} not found.")
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
def export_entries() -> None:
    """Export all entries as a JSON array."""
    with MemoryDB(state.db_path) as db:
        entries = db.list_entries(limit=None)
    typer.echo(json.dumps([dataclasses.asdict(e) for e in entries], indent=2))
