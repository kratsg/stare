"""Analysis CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from stare._output import stdout_is_interactive
from stare.cli import utils
from stare.dsl.errors import DSLError
from stare.exceptions import StareError
from stare.settings import StareSettings
from stare.urls import analysis_url

analysis_app = typer.Typer(
    help="Analysis commands (search and get).", rich_markup_mode="rich"
)


@analysis_app.command("search")
def analysis_search(
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Filter query (e.g. 'referenceCode = HION'; ops: =, !=, contain, not-contain; combine with and/or). See docs/query-dsl.md.",
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
) -> None:
    """Search analyses via GET /searchAnalysis.

    Output auto-detects: Rich table when stdout is a terminal, JSON when piped.
    Override with [cyan]--json[/cyan] or [cyan]--no-json[/cyan].

    [bold]Examples[/bold]
      [green]stare analysis search -q 'referenceCode = HION'[/green]
      [green]stare analysis search -q 'metadata.keywords contain jets and status = Active'[/green]
      [green]stare analysis search | jq '.results[].referenceCode'[/green]
      [green]stare analysis search | jq '[.results[] | select(.status=="Active")] | length'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-analysis-searchAnalysis
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.analyses.search(
            query=query,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
            validate_query=validate,
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
    table = Table(title=f"Analyses ({result.number_of_results} total)")
    table.add_column("Reference Code", style="cyan")
    table.add_column("Status")
    table.add_column("Short Title")
    for item in result.results:
        ref = item.reference_code or ""
        ref_cell = (
            f"[link={analysis_url(ref, web_base=settings.web_base_url)}]{ref}[/link]"
            if ref
            else ""
        )
        table.add_row(ref_cell, item.status or "", item.short_title or "")
    utils.console.print(table)


@analysis_app.command("get")
def analysis_get(
    ref_code: Annotated[str, typer.Argument(help="Analysis reference code")],
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
) -> None:
    """Fetch a single analysis by reference code via GET /analyses/{ref_code}.

    [bold]Examples[/bold]
      [green]stare analysis get ANA-HION-2018-01[/green]
      [green]stare analysis get ANA-HION-2018-01 | jq '.phase0.state'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-analysis-getAnalysis
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.analyses.get(ref_code)
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    ref = result.reference_code or ""
    url = analysis_url(ref, web_base=settings.web_base_url) if ref else None
    ref_markup = f"[link={url}]{ref}[/link]" if url else ref
    utils.console.print(f"[bold cyan]{ref_markup}[/bold cyan]  {result.status or ''}")
    if result.short_title:
        utils.console.print(result.short_title)
