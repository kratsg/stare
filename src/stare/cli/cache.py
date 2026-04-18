"""Cache management CLI commands."""

from __future__ import annotations

import sys
from typing import Annotated

import typer

from stare.cli import utils

cache_app = typer.Typer(help="HTTP cache management commands.", rich_markup_mode="rich")


@cache_app.command("info")
def cache_info() -> None:
    """Show cache directory, database path, TTL, and on-disk size."""
    settings = utils.make_settings()
    cache_dir = settings.get_cache_dir()
    db_path = cache_dir / "cache.db"
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
    db_path = settings.get_cache_dir() / "cache.db"
    if not confirm and sys.stdin.isatty():
        typer.confirm(f"Delete {db_path}?", abort=True)
    if db_path.exists():
        db_path.unlink()
        utils.console.print(f"[green]Cache cleared:[/green] {db_path}")
    else:
        utils.console.print(f"[dim]Nothing to clear:[/dim] {db_path} does not exist.")
