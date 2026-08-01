"""Publications CLI commands."""

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
from stare.urls import analysis_url, confnote_url, paper_url, pubnote_url

if TYPE_CHECKING:
    from stare.models import PublicationSearchResult, PublicationSummary

publications_app = typer.Typer(
    help="Publication search commands.", rich_markup_mode="rich"
)

_TYPE_URL_MAP = {
    "Analysis": analysis_url,
    "Paper": paper_url,
    "CONF note": confnote_url,
    "PUB note": pubnote_url,
}


def _render_search_table(result: PublicationSearchResult) -> None:
    settings = get_settings()
    table = Table(title=f"Publications ({result.number_of_results} total)")
    table.add_column("Reference Code", style="cyan")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Short Title")
    for item in result.results:
        ref = (
            item.final_reference_code
            or item.reference_code
            or item.temporary_reference_code
            or ""
        )
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


def _render_get_table(result: PublicationSummary, *, ref_code: str) -> None:
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


_SEARCH_SPEC = SearchSpec(
    accessor=lambda g: g.publications,
    render=_render_search_table,
    check_offset=False,
)


@publications_app.command("search")
def publications_search(
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Filter query (e.g. 'type = Paper'; fields: referenceCode, type, status, shortTitle, groups.leadingGroup, groups.subgroups).",
        ),
    ] = None,
    limit: LimitOption = 50,
    offset: OffsetOption = 0,
    sort_by: Annotated[
        str | None,
        typer.Option("--sort-by", help="camelCase API field to sort by."),
    ] = None,
    sort_desc: SortDescOption = False,
    output_json: JsonOption = None,
    no_cache: NoCacheOption = False,
    validate: ValidateOption = True,
    verbose: VerboseOption = False,
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


@publications_app.command("get")
def publications_get(
    ref_code: Annotated[str, typer.Argument(help="Publication reference code")],
    output_json: JsonOption = None,
    no_cache: NoCacheOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Fetch a single publication by reference code via GET /searchPublication.

    [bold]Examples[/bold]
      [green]stare publications get HDBS-2018-33[/green]
      [green]stare publications get ATLAS-CONF-2024-001 --json[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-Publication-searchPublication
    """
    # Built per-call (not a module-level _GET_SPEC like the other resources)
    # because render needs ref_code in its closure: _render_get_table falls
    # back to the requested ref_code when the response has no reference code.
    run_get(
        GetSpec(
            accessor=lambda g, ref, verbose: g.publications.get(ref, verbose=verbose),
            render=lambda result: _render_get_table(result, ref_code=ref_code),
        ),
        ref_code,
        output_json=output_json,
        no_cache=no_cache,
        verbose=verbose,
    )
