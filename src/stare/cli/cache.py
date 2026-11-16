"""Cache management CLI commands."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Annotated

import typer

from stare.cli import utils

if TYPE_CHECKING:
    from pathlib import Path

# The database file hishel 1.x writes; hishel 2.x never reads it, so clearing
# the cache removes it as well.
_LEGACY_DB_NAME = "cache.db"


def _sqlite_files(db_path: Path) -> list[Path]:
    """Return the database plus the -wal/-shm files SQLite keeps beside it.

    In WAL mode these outlive a crashed process, and a stale WAL could be
    replayed into the next database created under the same name.
    """
    return [db_path, *(db_path.with_name(db_path.name + s) for s in ("-wal", "-shm"))]


cache_app = typer.Typer(help="HTTP cache management commands.", rich_markup_mode="rich")


@cache_app.command("info")
def cache_info() -> None:
    """Show cache directory, database path, TTL, and on-disk size."""
    settings = utils.make_settings()
    cache_dir = settings.get_cache_dir()
    db_path = settings.get_cache_db_path()
    size = db_path.stat().st_size if db_path.exists() else 0
    size_display = f"{utils.sizeof_fmt(size)} ({size} bytes)"
    utils.console.print(f"Enabled:   {settings.cache_enabled}")
    utils.console.print(f"Directory: {cache_dir}")
    utils.console.print(f"Database:  {db_path}")
    utils.console.print(f"TTL:       {settings.cache_ttl_seconds} s")
    utils.console.print(f"Size:      {size_display}")


@cache_app.command("clear")
def cache_clear(
    confirm: Annotated[
        bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")
    ] = False,
) -> None:
    """Delete every cached response."""
    settings = utils.make_settings()
    db_path = settings.get_cache_db_path()
    legacy_path = settings.get_cache_dir() / _LEGACY_DB_NAME
    if not confirm and sys.stdin.isatty():
        typer.confirm(f"Delete {db_path}?", abort=True)
    existing = [
        path
        for db in (db_path, legacy_path)
        for path in _sqlite_files(db)
        if path.exists()
    ]
    for path in existing:
        path.unlink()
        utils.console.print(f"[green]Cache cleared:[/green] {path}")
    if not existing:
        utils.console.print(f"[dim]Nothing to clear:[/dim] {db_path} does not exist.")
