"""Paper CLI commands."""

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
from stare.urls import paper_url

if TYPE_CHECKING:
    from stare.models import PaperSearchResult

paper_app = typer.Typer(
    help="Paper commands (search and get).", rich_markup_mode="rich"
)


def _render_search_table(result: PaperSearchResult) -> None:
    settings = get_settings()
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


_SEARCH_SPEC = SearchSpec(accessor=lambda g: g.papers, render=_render_search_table)
_GET_SPEC = GetSpec(
    accessor=lambda g, ref, verbose: g.papers.get(ref, verbose=verbose),
    render=utils.console.print,
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
    limit: LimitOption = 50,
    offset: OffsetOption = 0,
    sort_by: Annotated[
        str | None,
        typer.Option(
            "--sort-by",
            help="camelCase API field to sort by (e.g. referenceCode, creationDate).",
        ),
    ] = None,
    sort_desc: SortDescOption = False,
    output_json: JsonOption = None,
    no_cache: NoCacheOption = False,
    validate: ValidateOption = True,
    verbose: VerboseOption = False,
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


@paper_app.command("get")
def paper_get(
    ref_code: Annotated[str, typer.Argument(help="Paper reference code")],
    output_json: JsonOption = None,
    no_cache: NoCacheOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Fetch a single paper by reference code via GET /searchPaper.

    [bold]Examples[/bold]
      [green]stare paper get HDBS-2018-33[/green]
      [green]stare paper get HDBS-2018-33 | jq '.phase1.state'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-paper-searchPaper
    """
    run_get(
        _GET_SPEC, ref_code, output_json=output_json, no_cache=no_cache, verbose=verbose
    )
