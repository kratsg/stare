"""Leading-group CLI commands."""

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
from stare.cli._shared import SearchOptions, SearchSpec, run_search

if TYPE_CHECKING:
    from stare.models import LeadingGroupSearchResult

leadinggroup_app = typer.Typer(
    help="Leading-group search commands.", rich_markup_mode="rich"
)


def _render_search_table(result: LeadingGroupSearchResult) -> None:
    table = Table(title=f"Leading Groups ({result.number_of_results} total)")
    table.add_column("Name", style="cyan")
    for item in result.results:
        table.add_row(item.name or "")
    utils.console.print(table)


_SEARCH_SPEC = SearchSpec(
    accessor=lambda g: g.leadinggroups,
    render=_render_search_table,
    check_offset=False,
)


@leadinggroup_app.command("search")
def leadinggroup_search(
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Filter query (e.g. 'name = SUSY'; ops: =, !=, contain, not-contain).",
        ),
    ] = None,
    limit: LimitOption = 50,
    offset: OffsetOption = 0,
    sort_by: Annotated[
        str | None,
        typer.Option("--sort-by", help="Field to sort by."),
    ] = None,
    sort_desc: SortDescOption = False,
    output_json: JsonOption = None,
    no_cache: NoCacheOption = False,
    validate: ValidateOption = True,
    verbose: VerboseOption = False,
) -> None:
    """Search leading groups via GET /searchLeadingGroup.

    Output auto-detects: Rich table when stdout is a terminal, JSON when piped.
    Override with [cyan]--json[/cyan] or [cyan]--no-json[/cyan].

    [bold]Examples[/bold]
      [green]stare leadinggroups search[/green]
      [green]stare leadinggroups search -q 'name = SUSY'[/green]
      [green]stare leadinggroups search | jq '[.results[].name]'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-LeadingGroup-searchLeadingGroup
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
