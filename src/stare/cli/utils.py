"""Shared utilities for the stare CLI."""

from __future__ import annotations

import json
import logging

from rich.console import Console
from rich.json import JSON
from rich.panel import Panel

from stare.auth import TokenManager
from stare.client import Glance
from stare.exceptions import ResponseParseError, StareError
from stare.settings import StareSettings

console = Console()
err_console = Console(stderr=True)


def sizeof_fmt(num: float, suffix: str = "B") -> str:
    """Format a byte count as a human-readable string (e.g. 1.0KiB)."""
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def handle_error(exc: StareError) -> None:
    """Print a StareError to stderr; for ResponseParseError also show the raw JSON."""
    err_console.print(f"[red]Error:[/red] {exc}")
    if isinstance(exc, ResponseParseError) and exc.raw_data is not None:
        err_console.print(
            Panel(
                JSON(json.dumps(exc.raw_data, default=str)),
                title="[yellow]Raw API Response[/yellow]",
                border_style="yellow",
            )
        )


def configure_verbose_logging() -> None:
    """Enable DEBUG-level request/response logging for httpx and httpcore."""
    logging.basicConfig(level=logging.DEBUG)
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.DEBUG)


def make_settings() -> StareSettings:
    settings = StareSettings()
    if settings.verbose:
        configure_verbose_logging()
    return settings


def make_token_manager() -> TokenManager:
    return TokenManager(make_settings())


def make_glance(no_cache: bool = False) -> Glance:
    settings = make_settings()
    if no_cache:
        settings = settings.model_copy(update={"cache_enabled": False})
    return Glance(settings=settings)
