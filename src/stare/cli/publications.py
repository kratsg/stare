"""Publications CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from stare._output import stdout_is_interactive
from stare.cli import utils
from stare.dsl.errors import DSLError
from stare.exceptions import StareError
from stare.settings import StareSettings
from stare.urls import analysis_url, confnote_url, paper_url, pubnote_url

publications_app = typer.Typer(
    help="Publication search commands.", rich_markup_mode="rich"
)

_TYPE_URL_MAP = {
    "Analysis": analysis_url,
    "Paper": paper_url,
    "CONF note": confnote_url,
    "PUB note": pubnote_url,
}


@publications_app.command("search")
def publications_search(
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Filter query (e.g. 'type = Paper'; fields: referenceCode, type, status, shortTitle, groups.leadingGroup.name, groups.subgroups.name).",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit", "-n", help="Max results to return (server default: 50)."
        ),
    ] = 50,
    offset: Annotated[
        int, typer.Option("--offset", help="Result offset for pagination.")
    ] = 0,
    sort_by: Annotated[
        str | None,
        typer.Option("--sort-by", help="camelCase API field to sort by."),
    ] = None,
    sort_desc: Annotated[
        bool, typer.Option("--sort-desc", help="Sort descending.")
    ] = False,
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
    validate: Annotated[
        bool,
        typer.Option(
            "--validate/--no-validate",
            help="Validate and normalize the query string (default: on).",
        ),
    ] = True,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Attach the full raw API response to parse errors (useful for debugging).",
        ),
    ] = False,
) -> None:
    """Search across all publication types via GET /searchPublication.

    Output auto-detects: Rich table when stdout is a terminal, JSON when piped.
    Override with [cyan]--json[/cyan] or [cyan]--no-json[/cyan].

    [bold]Examples[/bold]
      [green]stare publications search -q 'type = Paper'[/green]
      [green]stare publications search -q 'groups.leadingGroup.name = HDBS AND status = Active'[/green]
      [green]stare publications search -q 'referenceCode = ATLAS-CONF-2021-010'[/green]
      [green]stare publications search | jq '.results[].referenceCode'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-Publication-searchPublication
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.publications.search(
            query=query,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
            validate_query=validate,
            verbose=verbose,
        )
    except DSLError as exc:
        raise typer.BadParameter(str(exc), param_hint="--query") from exc
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    table = Table(title=f"Publications ({result.number_of_results} total)")
    table.add_column("Reference Code", style="cyan")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Short Title")
    for item in result.results:
        ref = item.reference_code or item.temporary_reference_code or ""
        url_fn = _TYPE_URL_MAP.get(item.type or "")
        ref_cell = (
            f"[link={url_fn(ref, web_base=settings.web_base_url)}]{ref}[/link]"
            if ref and url_fn
            else ref
        )
        table.add_row(
            ref_cell, item.type or "", item.status or "", item.short_title or ""
        )
    utils.console.print(table)


@publications_app.command("get")
def publications_get(
    ref_code: Annotated[str, typer.Argument(help="Publication reference code")],
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
    """Fetch a single publication by reference code via GET /searchPublication.

    [bold]Examples[/bold]
      [green]stare publications get HDBS-2018-33[/green]
      [green]stare publications get ATLAS-CONF-2024-001 --json[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-Publication-searchPublication
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.publications.get(ref_code, verbose=verbose)
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    table = Table(title="Publication")
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")
    ref = result.reference_code or result.temporary_reference_code or ref_code
    table.add_row("Reference Code", ref)
    if result.final_reference_code:
        table.add_row("Final Reference Code", result.final_reference_code)
    table.add_row("Type", result.type or "")
    table.add_row("Status", result.status or "")
    table.add_row("Short Title", result.short_title or "")
    utils.console.print(table)
