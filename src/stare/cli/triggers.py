"""Triggers CLI commands."""

from __future__ import annotations

import re
from typing import Annotated

import typer
from rich.table import Table
from rich.text import Text

from stare._output import stdout_is_interactive
from stare.cli import utils
from stare.dsl.errors import DSLError
from stare.exceptions import StareError

# Order matters: check bj before j, tau/xe/met/ht before their prefixes.
_OBJ_RE = re.compile(r"^(\d*)(bj|tau|xe|met|ht|j|e|g|mu)(\d+.*)$")

_OBJ_STYLES: dict[str, str] = {
    "e": "bold cyan",
    "mu": "bold magenta",
    "j": "bold yellow",
    "bj": "bold yellow3",
    "g": "bold green",
    "tau": "bold blue",
    "xe": "bold red",
    "met": "bold red",
    "ht": "bold orange3",
}

_WP_TOKENS: frozenset[str] = frozenset(
    {
        "lhloose",
        "lhmedium",
        "lhvloose",
        "lhtight",
        "loose",
        "medium",
        "tight",
        "medium1",
        "etcut",
        "ivarloose",
        "ivarmedium",
        "ivartight",
        "ivarmedium1",
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
        typer.Option("--sort-by", help="Field to sort by."),
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
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.triggers.search(
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

    table = Table(title=f"Triggers ({result.number_of_results} total)")
    table.add_column("Name")
    table.add_column("Year")
    table.add_column("Category")
    for trigger in result.results:
        table.add_row(
            _render_trigger_name(trigger.name or ""),
            trigger.year or "",
            trigger.category.name if trigger.category else "",
        )
    utils.console.print(table)
