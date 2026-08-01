"""Plot CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
from rich.table import Table

from stare.cli import utils
from stare.cli._params import (
    JsonOption,
    LimitOption,
    NoCacheOption,
    OffsetOption,
    SortDescOption,
    ValidateOption,
    VerboseOption,
)
from stare.cli._shared import GetSpec, SearchOptions, SearchSpec, run_get, run_search
from stare.settings import get_settings
from stare.urls import plot_url

if TYPE_CHECKING:
    from stare.models import PlotSearchResult

plot_app = typer.Typer(
    help="Approval plot commands (search and get).", rich_markup_mode="rich"
)


def _render_search_table(result: PlotSearchResult) -> None:
    settings = get_settings()
    table = Table(title=f"Plots ({result.number_of_results} total)")
    table.add_column("Reference Code", style="cyan")
    table.add_column("Status")
    table.add_column("Short Title")
    for item in result.results:
        ref = item.reference_code or ""
        ref_cell = f"[link={plot_url(ref, web_base=settings.web_base_url)}]{ref}[/link]"
        table.add_row(ref_cell, item.status or "", item.short_title or "")
    utils.console.print(table)


_SEARCH_SPEC = SearchSpec(accessor=lambda g: g.plots, render=_render_search_table)
_GET_SPEC = GetSpec(
    accessor=lambda g, ref, verbose: g.plots.get(ref, verbose=verbose),
    render=utils.console.print,
)


@plot_app.command("search")
def plot_search(
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Filter query (e.g. 'referenceCode = PLOT-MUON-2018-08'; ops: =, !=, contain, not-contain; combine with and/or; quote values with spaces: 'phase1.state = \"Phase Closed\"'). See docs/query-dsl.md.",
        ),
    ] = None,
    limit: LimitOption = 50,
    offset: OffsetOption = 0,
    sort_by: Annotated[
        str | None,
        typer.Option(
            "--sort-by",
            help="camelCase API field to sort by (e.g. referenceCode).",
        ),
    ] = None,
    sort_desc: SortDescOption = False,
    output_json: JsonOption = None,
    no_cache: NoCacheOption = False,
    validate: ValidateOption = True,
    verbose: VerboseOption = False,
) -> None:
    """Search Plots via GET /searchPlot.

    Output auto-detects: Rich table when stdout is a terminal, JSON when piped.
    Override with [cyan]--json[/cyan] or [cyan]--no-json[/cyan].

    [bold]Examples[/bold]
      [green]stare plot search -q 'referenceCode contain PLOT-MUON'[/green]
      [green]stare plot search -q 'groups.leadingGroup.name = TRIG AND status = phase1_closed'[/green]
      [green]stare plot search | jq '.results[].referenceCode'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#/Plot/searchPlot
    """
    run_search(
        _SEARCH_SPEC,
        SearchOptions(
            query=query,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
            validate_query=validate,
            verbose=verbose,
        ),
        output_json=output_json,
        no_cache=no_cache,
    )


@plot_app.command("get")
def plot_get(
    ref_code: Annotated[str, typer.Argument(help="Plot reference code")],
    output_json: JsonOption = None,
    no_cache: NoCacheOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Fetch a single plot by reference code via GET /searchPlot.

    [bold]Examples[/bold]
      [green]stare plot get PLOT-MUON-2018-08[/green]
      [green]stare plot get PLOT-MUON-2018-08 | jq '.status'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#/Plot/searchPlot
    """
    run_get(
        _GET_SPEC, ref_code, output_json=output_json, no_cache=no_cache, verbose=verbose
    )
