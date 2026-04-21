"""Publications CLI commands."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.table import Table

from stare._output import stdout_is_interactive
from stare.cli import utils
from stare.exceptions import StareError

publications_app = typer.Typer(
    help="Publication search commands.", rich_markup_mode="rich"
)


@publications_app.command("search")
def publications_search(
    reference_code: Annotated[
        list[str] | None, typer.Option("--ref", help="Filter by reference code")
    ] = None,
    type_: Annotated[
        list[str] | None,
        typer.Option("--type", help="Filter by type (Paper, ConfNote, PubNote)"),
    ] = None,
    leading_group: Annotated[
        list[str] | None, typer.Option("--group", help="Filter by leading group")
    ] = None,
    subgroup: Annotated[
        list[str] | None, typer.Option("--subgroup", help="Filter by subgroup")
    ] = None,
    status: Annotated[
        list[str] | None, typer.Option("--status", help="Filter by status")
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
    """Search across all publication types via GET /publications/search.

    Returns Papers, CONF notes, and PUB notes in a single result set.

    [bold]Examples[/bold]
      [green]stare publications search --type Paper --group HDBS[/green]
      [green]stare publications search | jq '.[].referenceCode'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-publications-searchPublications
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        results = g.publications.search(
            reference_codes=reference_code or None,
            types=type_ or None,
            leading_groups=leading_group or None,
            subgroups=subgroup or None,
            statuses=status or None,
            verbose=verbose,
        )
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(json.dumps([r.model_dump(by_alias=True) for r in results]))
        return

    table = Table(title="Publications")
    table.add_column("Reference Code", style="cyan")
    table.add_column("Type")
    for pub in results:
        table.add_row(pub.reference_code or "", pub.type or "")
    utils.console.print(table)
