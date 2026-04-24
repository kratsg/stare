"""Paper CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from stare._output import stdout_is_interactive
from stare.cli import utils
from stare.dsl.errors import DSLError
from stare.exceptions import StareError
from stare.settings import StareSettings
from stare.urls import paper_url

paper_app = typer.Typer(
    help="Paper commands (search and get).", rich_markup_mode="rich"
)


@paper_app.command("search")
def paper_search(
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Filter query (e.g. 'referenceCode = HDBS'; ops: =, !=, contain, not-contain; combine with and/or; quote values with spaces: 'phase2.state = \"Phase Closed\"'). See docs/query-dsl.md.",
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
            help="camelCase API field to sort by (e.g. referenceCode, creationDate).",
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
    """Search papers via GET /searchPaper.

    Output auto-detects: Rich table when stdout is a terminal, JSON when piped.
    Override with [cyan]--json[/cyan] or [cyan]--no-json[/cyan].

    [bold]Examples[/bold]
      [green]stare paper search -q 'referenceCode = HDBS'[/green]
      [green]stare paper search -q 'fullTitle contain Higgs'[/green]
      [green]stare paper search -q 'phase2.state = "Phase Closed"'[/green]
      [green]stare paper search | jq '.results[].referenceCode'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-paper-searchPaper
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.papers.search(
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
    table = Table(title=f"Papers ({result.number_of_results} total)")
    table.add_column("Reference Code", style="cyan")
    table.add_column("Status")
    table.add_column("Short Title")
    for item in result.results:
        ref = item.reference_code or ""
        ref_cell = (
            f"[link={paper_url(ref, web_base=settings.web_base_url)}]{ref}[/link]"
            if ref
            else ""
        )
        table.add_row(ref_cell, item.status or "", item.short_title or "")
    utils.console.print(table)


@paper_app.command("get")
def paper_get(
    ref_code: Annotated[str, typer.Argument(help="Paper reference code")],
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
    """Fetch a single paper by reference code via GET /papers/{ref_code}.

    [bold]Examples[/bold]
      [green]stare paper get HDBS-2018-33[/green]
      [green]stare paper get HDBS-2018-33 | jq '.phase1.state'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-paper-getPaper
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.papers.get(ref_code, verbose=verbose)
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    utils.console.print(result)
