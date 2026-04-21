"""Triggers CLI commands."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.table import Table

from stare._output import stdout_is_interactive
from stare.cli import utils
from stare.exceptions import StareError

triggers_app = typer.Typer(help="Trigger search commands.", rich_markup_mode="rich")


@triggers_app.command("search")
def triggers_search(
    category: Annotated[
        list[str] | None, typer.Option("--category", help="Filter by trigger category")
    ] = None,
    year: Annotated[
        list[str] | None, typer.Option("--year", help="Filter by year")
    ] = None,
    output_json: Annotated[
        bool | None,
        typer.Option(
            "--json/--no-json",
            help="Emit JSON. Default: auto (JSON when piped, Rich table when interactive).",
        ),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Bypass the HTTP cache for this invocation."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Attach the full raw API response to parse errors (useful for debugging).",
        ),
    ] = False,
) -> None:
    """Search HLT triggers via GET /triggers/search.

    [bold]Examples[/bold]
      [green]stare triggers search --category electron --year 2018[/green]
      [green]stare triggers search | jq '.[].name'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-triggers-searchTriggers
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        results = g.triggers.search(
            categories=category or None,
            years=year or None,
            verbose=verbose,
        )
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(json.dumps([r.model_dump(by_alias=True) for r in results]))
        return

    table = Table(title="Triggers")
    table.add_column("Name", style="cyan")
    table.add_column("Category")
    table.add_column("Year")
    for trigger in results:
        cat_name = trigger.category.name if trigger.category else ""
        cat_year = trigger.category.year if trigger.category else ""
        table.add_row(trigger.name or "", cat_name or "", cat_year or "")
    utils.console.print(table)
