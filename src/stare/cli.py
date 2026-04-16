"""CLI entry point for stare."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from stare import __version__
from stare.auth import TokenManager
from stare.client import Glance
from stare.exceptions import StareError
from stare.settings import StareSettings

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(
    name="stare",
    help="ATLAS Glance/Fence API — Python library and CLI.",
    no_args_is_help=True,
)

auth_app = typer.Typer(help="Authentication commands.")
app.add_typer(auth_app, name="auth")

publications_app = typer.Typer(help="Publication search commands.")
app.add_typer(publications_app, name="publications")

triggers_app = typer.Typer(help="Trigger search commands.")
app.add_typer(triggers_app, name="triggers")


def _make_settings() -> StareSettings:
    return StareSettings()


def _make_token_manager() -> TokenManager:
    return TokenManager(_make_settings())


def _make_glance() -> Glance:
    return Glance()


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


@app.command()
def version() -> None:
    """Show the stare version."""
    console.print(f"stare {__version__}")


# ---------------------------------------------------------------------------
# login / logout / auth status
# ---------------------------------------------------------------------------


@app.command()
def login() -> None:
    """Authenticate with CERN SSO using OAuth2 PKCE."""
    tm = _make_token_manager()
    try:
        console.print("Opening browser for CERN SSO authentication...")
        tm.login()
        console.print("[green]✓[/green] Authentication successful.")
    except StareError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def logout() -> None:
    """Remove stored authentication tokens."""
    tm = _make_token_manager()
    tm.logout()
    console.print("Logged out.")


@auth_app.command("status")
def auth_status() -> None:
    """Show current authentication status."""
    tm = _make_token_manager()
    if tm.is_authenticated():
        console.print("[green]Authenticated[/green]")
    else:
        console.print(
            "Not authenticated. Run [bold]stare login[/bold] to authenticate."
        )


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@app.command()
def search(
    query: Annotated[
        str | None, typer.Option("--query", "-q", help="Filter query string")
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Max results to return")
    ] = 50,
    offset: Annotated[
        int, typer.Option("--offset", help="Result offset (pagination)")
    ] = 0,
    sort_by: Annotated[
        str | None, typer.Option("--sort-by", help="Field to sort by")
    ] = None,
    sort_desc: Annotated[
        bool, typer.Option("--sort-desc", help="Sort descending")
    ] = False,
    output_json: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
) -> None:
    """Search analyses."""
    g = _make_glance()
    try:
        result = g.analyses.search(
            query=query,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
    except StareError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    table = Table(title=f"Analyses ({result.total_rows} total)")
    table.add_column("Reference Code", style="cyan")
    table.add_column("Status")
    table.add_column("Short Title")
    for analysis in result.results:
        table.add_row(
            analysis.reference_code or "",
            analysis.status or "",
            analysis.short_title or "",
        )
    console.print(table)


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------


@app.command()
def analysis(
    ref_code: Annotated[str, typer.Argument(help="Analysis reference code")],
    output_json: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
) -> None:
    """Fetch a single analysis by reference code."""
    g = _make_glance()
    try:
        result = g.analyses.get(ref_code)
    except StareError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    console.print(
        f"[bold cyan]{result.reference_code}[/bold cyan]  {result.status or ''}"
    )
    if result.short_title:
        console.print(result.short_title)


# ---------------------------------------------------------------------------
# paper
# ---------------------------------------------------------------------------


@app.command()
def paper(
    ref_code: Annotated[str, typer.Argument(help="Paper reference code")],
    output_json: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
) -> None:
    """Fetch a single paper by reference code."""
    g = _make_glance()
    try:
        result = g.papers.get(ref_code)
    except StareError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    console.print(
        f"[bold cyan]{result.reference_code}[/bold cyan]  {result.status or ''}"
    )
    if result.short_title:
        console.print(result.short_title)


# ---------------------------------------------------------------------------
# conf-note
# ---------------------------------------------------------------------------


@app.command(name="conf-note")
def conf_note(
    ref_code: Annotated[str, typer.Argument(help="CONF note temporary reference code")],
    output_json: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
) -> None:
    """Fetch a single CONF note by temporary reference code."""
    g = _make_glance()
    try:
        result = g.conf_notes.get(ref_code)
    except StareError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    console.print(
        f"[bold cyan]{result.temp_reference_code}[/bold cyan]  {result.status or ''}"
    )
    if result.short_title:
        console.print(result.short_title)


# ---------------------------------------------------------------------------
# pub-note
# ---------------------------------------------------------------------------


@app.command(name="pub-note")
def pub_note(
    ref_code: Annotated[str, typer.Argument(help="PUB note temporary reference code")],
    output_json: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
) -> None:
    """Fetch a single PUB note by temporary reference code."""
    g = _make_glance()
    try:
        result = g.pub_notes.get(ref_code)
    except StareError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    console.print(
        f"[bold cyan]{result.temp_reference_code}[/bold cyan]  {result.status or ''}"
    )
    if result.short_title:
        console.print(result.short_title)


# ---------------------------------------------------------------------------
# publications search
# ---------------------------------------------------------------------------


@publications_app.command("search")
def publications_search(
    reference_code: Annotated[
        list[str] | None, typer.Option("--ref", help="Filter by reference code")
    ] = None,
    type_: Annotated[
        list[str] | None,
        typer.Option("--type", help="Filter by type (Paper, ConfNote, PubNote)"),
    ] = None,
    leading_group: Annotated[
        list[str] | None, typer.Option("--group", help="Filter by leading group")
    ] = None,
    subgroup: Annotated[
        list[str] | None, typer.Option("--subgroup", help="Filter by subgroup")
    ] = None,
    status: Annotated[
        list[str] | None, typer.Option("--status", help="Filter by status")
    ] = None,
    output_json: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
) -> None:
    """Search across all publication types."""
    g = _make_glance()
    try:
        results = g.publications.search(
            reference_codes=reference_code or None,
            types=type_ or None,
            leading_groups=leading_group or None,
            subgroups=subgroup or None,
            statuses=status or None,
        )
    except StareError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(json.dumps([r.model_dump(by_alias=True) for r in results]))
        return

    table = Table(title="Publications")
    table.add_column("Reference Code", style="cyan")
    table.add_column("Type")
    for pub in results:
        table.add_row(pub.reference_code or "", pub.type or "")
    console.print(table)


# ---------------------------------------------------------------------------
# groups / subgroups
# ---------------------------------------------------------------------------


@app.command()
def groups(
    output_json: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
) -> None:
    """List all leading groups."""
    g = _make_glance()
    try:
        result = g.groups.list()
    except StareError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(json.dumps(result))
        return

    for group in result:
        console.print(group)


@app.command()
def subgroups(
    output_json: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
) -> None:
    """List all subgroups."""
    g = _make_glance()
    try:
        result = g.subgroups.list()
    except StareError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(json.dumps(result))
        return

    for sg in result:
        console.print(sg)


# ---------------------------------------------------------------------------
# triggers search
# ---------------------------------------------------------------------------


@triggers_app.command("search")
def triggers_search(
    category: Annotated[
        list[str] | None, typer.Option("--category", help="Filter by trigger category")
    ] = None,
    year: Annotated[
        list[str] | None, typer.Option("--year", help="Filter by year")
    ] = None,
    output_json: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
) -> None:
    """Search triggers."""
    g = _make_glance()
    try:
        results = g.triggers.search(
            categories=category or None,
            years=year or None,
        )
    except StareError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(json.dumps([r.model_dump(by_alias=True) for r in results]))
        return

    table = Table(title="Triggers")
    table.add_column("Name", style="cyan")
    table.add_column("Category")
    table.add_column("Year")
    for trigger in results:
        cat_name = trigger.category.name if trigger.category else ""
        cat_year = trigger.category.year if trigger.category else ""
        table.add_row(trigger.name or "", cat_name or "", cat_year or "")
    console.print(table)
