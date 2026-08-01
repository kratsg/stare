"""Subgroup CLI commands."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Annotated

import typer
from rich.columns import Columns
from rich.panel import Panel

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
    from stare.models import SubgroupSearchResult

subgroup_app = typer.Typer(help="Subgroup search commands.", rich_markup_mode="rich")


def _render_search_table(result: SubgroupSearchResult) -> None:
    groups: dict[str, list[str]] = defaultdict(list)
    for item in result.results:
        name = item.name or ""
        prefix, _, suffix = name.partition("-")
        groups[prefix].append(suffix or name)

    panels = [
        Panel("\n".join(sorted(subs)), title=f"[bold]{prefix}[/bold]", expand=False)
        for prefix, subs in sorted(groups.items())
    ]
    utils.console.print(
        Columns(panels, title=f"Subgroups ({result.number_of_results} total)")
    )


_SEARCH_SPEC = SearchSpec(
    accessor=lambda g: g.subgroups,
    render=_render_search_table,
    check_offset=False,
)


@subgroup_app.command("search")
def subgroup_search(
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Filter query (e.g. 'name contain HIGG'; ops: =, !=, contain, not-contain).",
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
    """Search subgroups via GET /searchSubgroup.

    Output auto-detects: Rich table when stdout is a terminal, JSON when piped.
    Override with [cyan]--json[/cyan] or [cyan]--no-json[/cyan].

    [bold]Examples[/bold]
      [green]stare subgroups search[/green]
      [green]stare subgroups search -q 'name contain HIGG'[/green]
      [green]stare subgroups search | jq '[.results[].name]'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-Subgroup-searchSubgroup
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
