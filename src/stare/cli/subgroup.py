"""Subgroup CLI commands."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated

import typer
from rich.columns import Columns
from rich.panel import Panel

from stare._output import stdout_is_interactive
from stare.cli import utils
from stare.dsl.errors import DSLError
from stare.exceptions import StareError

subgroup_app = typer.Typer(help="Subgroup search commands.", rich_markup_mode="rich")


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
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.subgroups.search(
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
