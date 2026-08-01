"""Triggers CLI commands."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Annotated

import typer
from rich.table import Table
from rich.text import Text

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
    from stare.models import TriggerSearchResult

# Order matters: longer/more-specific prefixes before their single-char subsets.
_OBJ_RE = re.compile(r"^(\d*)(bj|tau|xs|xe|met|ht|j|e|g|mu)(\d+.*)$")

_OBJ_STYLES: dict[str, str] = {
    "e": "bold cyan",
    "mu": "bold magenta",
    "j": "bold yellow",
    "bj": "bold yellow3",
    "g": "bold green",
    "tau": "bold blue",
    "xe": "bold red",
    "xs": "bold red",
    "met": "bold red",
    "ht": "bold orange3",
}

_CATEGORY_STYLES: dict[str, str] = {
    "primary": "bold on dark_green",
    "backup": "green",
    "disabled": "dim grey62",
}


def _render_category(name: str) -> Text:
    """Style a trigger category name for Rich display."""
    return Text(name, style=_CATEGORY_STYLES.get(name, ""))


_WP_TOKENS: frozenset[str] = frozenset(
    {
        "lhloose",
        "lhmedium",
        "lhvloose",
        "lhtight",
        "vloose",
        "iloose",
        "icalovloose",
        "icaloloose",
        "icalotight",
        "loose",
        "medium",
        "tight",
        "medium1",
        "etcut",
        "ivarloose",
        "ivarmedium",
        "ivartight",
        "ivarmedium1",
        "bmedium",
        "boffperf",
        "bperf",
        "btight",
    }
)


def _render_trigger_name(name: str) -> Text:
    """Heuristically style an ATLAS HLT trigger name for Rich display.

    Objects are coloured by type, working-point tokens italicised, the L1 seed
    suffix greyed out, and all other modifier tokens dimmed.  The plain-text
    content is identical to the original name — no information is lost.
    """
    text = Text(no_wrap=True, overflow="ellipsis")
    if not name:
        return text
    if not name.startswith("HLT_"):
        text.append(name)
        return text

    text.append("HLT_", style="dim")
    rest = name[4:]

    # Separate the L1 seed suffix (last _L1... segment).
    l1_part = ""
    l1_idx = rest.rfind("_L1")
    if l1_idx != -1:
        l1_part = rest[l1_idx + 1 :]  # drop the leading underscore
        rest = rest[:l1_idx]

    for i, tok in enumerate(rest.split("_")):
        if i > 0:
            text.append("_", style="dim")
        m = _OBJ_RE.match(tok)
        if m:
            text.append(tok, style=_OBJ_STYLES.get(m.group(2), "bold"))
        elif tok.lower() in _WP_TOKENS:
            text.append(tok, style="italic")
        else:
            text.append(tok, style="dim")

    if l1_part:
        text.append(f"_{l1_part}", style="grey62")

    return text


triggers_app = typer.Typer(help="Trigger search commands.", rich_markup_mode="rich")


def _render_search_table(result: TriggerSearchResult) -> None:
    table = Table(title=f"Triggers ({result.number_of_results} total)")
    table.add_column("Name")
    table.add_column("Year")
    table.add_column("Category")
    for trigger in result.results:
        table.add_row(
            _render_trigger_name(trigger.name or ""),
            trigger.year or "",
            _render_category(trigger.category.name),
        )
    utils.console.print(table)


_SEARCH_SPEC = SearchSpec(
    accessor=lambda g: g.triggers,
    render=_render_search_table,
    check_offset=False,
)


@triggers_app.command("search")
def triggers_search(
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Filter query (e.g. 'year = 2024'; 'category.name = L1 AND year = 2023'). Ops: =, !=, contain, not-contain.",
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
    """Search HLT triggers via GET /searchTrigger.

    Output auto-detects: Rich table when stdout is a terminal, JSON when piped.
    Override with [cyan]--json[/cyan] or [cyan]--no-json[/cyan].

    [bold]Examples[/bold]
      [green]stare triggers search -q 'year = 2024'[/green]
      [green]stare triggers search -q 'category.name = electron AND year = 2022'[/green]
      [green]stare triggers search | jq '[.results[].name]'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-Trigger-searchTrigger
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
