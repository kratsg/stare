"""PubNote CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from stare._output import stdout_is_interactive
from stare.cli import utils
from stare.dsl.errors import DSLError
from stare.exceptions import StareError
from stare.settings import StareSettings
from stare.urls import pubnote_url

pubnote_app = typer.Typer(
    help="PubNote commands (search and get).", rich_markup_mode="rich"
)


@pubnote_app.command("search")
def pubnote_search(
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Filter query (e.g. 'finalReferenceCode = ATL-PHYS-PUB-2024-01'; ops: =, !=, contain, not-contain; combine with and/or; quote values with spaces: 'phase1.state = \"Phase Closed\"'). See docs/query-dsl.md.",
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
        typer.Option(
            "--sort-by",
            help="camelCase API field to sort by (e.g. finalReferenceCode).",
        ),
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
    """Search PubNotes via GET /searchPubnote.

    Output auto-detects: Rich table when stdout is a terminal, JSON when piped.
    Override with [cyan]--json[/cyan] or [cyan]--no-json[/cyan].

    [bold]Examples[/bold]
      [green]stare pubnote search -q 'finalReferenceCode = ATL-PHYS-PUB-2024-01'[/green]
      [green]stare pubnote search -q 'fullTitle contain Higgs'[/green]
      [green]stare pubnote search -q 'phase1.state = "Phase Closed"'[/green]
      [green]stare pubnote search | jq '.results[].finalReferenceCode'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#/Pubnote/searchPubnote
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.pubnotes.search(
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

    if (result.number_of_results == 0 and offset > 0) or (
        result.number_of_results > 0 and offset >= result.number_of_results
    ):
        typer.echo(
            f"Invalid offset: {offset}. Maximum allowed offset is "
            f"{max(result.number_of_results - 1, 0)} for "
            f"{result.number_of_results} total results."
        )
        raise typer.Exit(2)

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    table = Table(title=f"PubNotes ({result.number_of_results} total)")
    table.add_column("Reference Code", style="cyan")
    table.add_column("Status")
    table.add_column("Short Title")
    for item in result.results:
        ref = item.final_reference_code or ""
        ref_cell = (
            f"[link={pubnote_url(ref, web_base=settings.web_base_url)}]{ref}[/link]"
            if ref
            else ""
        )
        table.add_row(ref_cell, item.status or "", item.short_title or "")
    utils.console.print(table)


@pubnote_app.command("get")
def pubnote_get(
    ref_code: Annotated[str, typer.Argument(help="PUB note final reference code")],
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
    """Fetch a single PUB note by final reference code via GET /searchPubnote.

    [bold]Examples[/bold]
      [green]stare pubnote get ATL-PHYS-PUB-2024-01[/green]
      [green]stare pubnote get ATL-PHYS-PUB-2024-01 | jq '.status'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#/Pubnote/searchPubnote
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.pubnotes.get(ref_code, verbose=verbose)
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    ref = result.final_reference_code or ""
    url = pubnote_url(ref, web_base=settings.web_base_url) if ref else None
    ref_markup = f"[link={url}]{ref}[/link]" if url else ref
    utils.console.print(f"[bold cyan]{ref_markup}[/bold cyan]  {result.status or ''}")
    if result.short_title:
        utils.console.print(result.short_title)
