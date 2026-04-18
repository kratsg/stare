"""CLI entry point for stare."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

from stare import __version__
from stare.auth import TokenManager
from stare.client import Glance
from stare.exceptions import ResponseParseError, StareError
from stare.projection import parse_specs, resolve
from stare.settings import StareSettings
from stare.urls import analysis_url, conf_note_url, paper_url, pub_note_url

console = Console()
err_console = Console(stderr=True)


def _render(value: object) -> Any:
    """Convert a resolved projection value to something Rich can render in a table cell."""
    if value is None:
        return ""
    if hasattr(value, "__rich__"):
        return value  # Rich-aware objects (e.g. Link) render themselves
    return str(value)


def _handle_error(exc: StareError) -> None:
    """Print a StareError to stderr; for ResponseParseError also show the raw JSON."""
    err_console.print(f"[red]Error:[/red] {exc}")
    if isinstance(exc, ResponseParseError) and exc.raw_data is not None:
        err_console.print(
            Panel(
                JSON(json.dumps(exc.raw_data, default=str)),
                title="[yellow]Raw API Response[/yellow]",
                border_style="yellow",
            )
        )


app = typer.Typer(
    name="stare",
    help="ATLAS Glance/Fence API — Python library and CLI.",
    no_args_is_help=True,
)

auth_app = typer.Typer(help="Authentication commands.")
app.add_typer(auth_app, name="auth")

analysis_app = typer.Typer(help="Analysis commands (search and get).")
app.add_typer(analysis_app, name="analysis")

paper_app = typer.Typer(help="Paper commands (search and get).")
app.add_typer(paper_app, name="paper")

publications_app = typer.Typer(help="Publication search commands.")
app.add_typer(publications_app, name="publications")

triggers_app = typer.Typer(help="Trigger search commands.")
app.add_typer(triggers_app, name="triggers")


def _make_settings() -> StareSettings:
    settings = StareSettings()
    if settings.verbose:
        _configure_verbose_logging()
    return settings


def _configure_verbose_logging() -> None:
    """Enable DEBUG-level request/response logging for httpx and httpcore."""
    logging.basicConfig(level=logging.DEBUG)
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.DEBUG)


def _make_token_manager() -> TokenManager:
    return TokenManager(_make_settings())


def _make_glance() -> Glance:
    return Glance(settings=_make_settings())


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


@app.command()
def version() -> None:
    """Show the stare version."""
    console.print(f"stare {__version__}")


# ---------------------------------------------------------------------------
# auth login / logout / status / info
# ---------------------------------------------------------------------------


@auth_app.command("login")
def auth_login() -> None:
    """Authenticate with CERN SSO using OAuth2 PKCE."""
    tm = _make_token_manager()

    def _on_url_ready(url: str) -> None:
        console.print(
            Panel(
                f"[dim]If your browser did not open, copy this URL:[/dim]\n\n"
                f"[bold cyan][link={url}]{url}[/link][/bold cyan]",
                title="[bold]CERN SSO Authentication[/bold]",
                border_style="blue",
                padding=(1, 2),
            ),
            crop=False,
        )
        console.print("[dim]Opening browser...[/dim]")

    def _get_manual_code() -> str | None:
        console.print()
        console.print(
            "[dim]If the redirect did not complete automatically, find the[/dim]\n"
            "[dim][bold]code=[/bold] value in the redirect URL and paste it below.[/dim]\n"
            "[dim](Press Enter to keep waiting for the automatic redirect.)[/dim]"
        )
        raw = typer.prompt("Authorization code", default="", show_default=False)
        return raw.strip() or None

    try:
        tm.login(on_url_ready=_on_url_ready, get_manual_code=_get_manual_code)
    except StareError as exc:
        _handle_error(exc)
        raise typer.Exit(1) from exc

    console.print("\n[green]✓[/green] Authenticated successfully.")


@auth_app.command("logout")
def auth_logout() -> None:
    """Remove stored authentication tokens."""
    tm = _make_token_manager()
    tm.logout()
    console.print("Logged out.")


@auth_app.command("status")
def auth_status() -> None:
    """Show current authentication status (quick check)."""
    tm = _make_token_manager()
    if tm.is_authenticated():
        console.print("[green]Authenticated[/green]")
    else:
        console.print(
            "Not authenticated. Run [bold]stare auth login[/bold] to authenticate."
        )


@auth_app.command("info")
def auth_info(
    exchange: Annotated[
        bool,
        typer.Option("--exchange", help="Show info for the RFC 8693 exchanged token"),
    ] = False,
    access_token: Annotated[
        bool,
        typer.Option(
            "--access-token", help="Print the raw access token instead of decoded info"
        ),
    ] = False,
    id_token: Annotated[
        bool,
        typer.Option(
            "--id-token", help="Print the raw id token instead of decoded info"
        ),
    ] = False,
) -> None:
    """Show detailed token information and decoded JWT claims."""
    tm = _make_token_manager()

    # --exchange --id-token is nonsensical: token exchange produces no id token
    if exchange and id_token:
        err_console.print("The RFC 8693 token exchange does not produce an id token.")
        raise typer.Exit(1)

    # Raw token output mode: print token string(s) and return
    if access_token or id_token:
        if access_token:
            if exchange:
                try:
                    tok = tm.get_exchange_access_token()
                except StareError as exc:
                    _handle_error(exc)
                    raise typer.Exit(1) from exc
                if tok is None:
                    err_console.print(
                        "Token exchange is not configured. "
                        "Set [bold]STARE_EXCHANGE_AUDIENCE[/bold] to enable."
                    )
                    raise typer.Exit(1)
            else:
                try:
                    tok = tm.get_pkce_access_token()
                except StareError as exc:
                    _handle_error(exc)
                    raise typer.Exit(1) from exc
            typer.echo(tok)
        if id_token:
            raw = tm.get_pkce_id_token()
            if raw is None:
                err_console.print("No id token is stored.")
                raise typer.Exit(1)
            typer.echo(raw)
        return

    if exchange:
        try:
            info = tm.get_exchange_token_info()
        except StareError as exc:
            _handle_error(exc)
            raise typer.Exit(1) from exc
        if info is None:
            err_console.print(
                "Token exchange is not configured. "
                "Set [bold]STARE_EXCHANGE_AUDIENCE[/bold] to enable."
            )
            raise typer.Exit(1)
        panel_title = "[bold]Exchange Token Info[/bold]"
    else:
        info = tm.get_token_info()
        if info is None:
            err_console.print(
                "Not authenticated. Run [bold]stare auth login[/bold] to authenticate."
            )
            raise typer.Exit(1)
        panel_title = "[bold]Auth Info[/bold]"

    exp: int = info.expires_at
    now = int(time.time())
    is_expired: bool = info.is_expired
    claims = info.claims

    expires_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
    if not is_expired:
        remaining = exp - now
        mins, secs = divmod(remaining, 60)
        expiry_label = f"[green]valid[/green] — expires in {mins}m {secs}s ({expires_dt.strftime('%Y-%m-%d %H:%M:%S %Z')})"
    else:
        expiry_label = (
            f"[red]expired[/red] ({expires_dt.strftime('%Y-%m-%d %H:%M:%S %Z')})"
        )

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Token", expiry_label)

    for api_key, label in [
        ("preferred_username", "Username"),
        ("name", "Name"),
        ("email", "Email"),
        ("sub", "Subject"),
        ("eduperson_orcid", "ORCID"),
        ("cern_person_id", "CERN Person ID"),
    ]:
        val = getattr(claims, api_key, None)
        if val:
            table.add_row(label, str(val))

    if claims.aud is not None:
        aud_str = ", ".join(claims.aud) if isinstance(claims.aud, list) else claims.aud
        table.add_row("Audience", aud_str)

    if claims.cern_roles:
        table.add_row("Roles", ", ".join(claims.cern_roles))

    console.print(Panel(table, title=panel_title, border_style="blue"))


# ---------------------------------------------------------------------------
# analysis search / get
# ---------------------------------------------------------------------------


@analysis_app.command("search")
def analysis_search(
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
    projection: Annotated[
        str | None,
        typer.Option(
            "--projection",
            "-p",
            help="Comma-separated field paths, e.g. referenceCode,groups.leadingGroup",
        ),
    ] = None,
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
        _handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    table = Table(title=f"Analyses ({result.total_rows} total)")
    if projection:
        specs = parse_specs(projection)
        for spec in specs:
            table.add_column(spec.header)
        for item in result.results:
            table.add_row(*[_render(resolve(item, s.path)) for s in specs])
    else:
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
    console.print(table)


@analysis_app.command("get")
def analysis_get(
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
        _handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    ref = result.reference_code or ""
    url = analysis_url(ref, web_base=settings.web_base_url) if ref else None
    ref_markup = f"[link={url}]{ref}[/link]" if url else ref
    console.print(f"[bold cyan]{ref_markup}[/bold cyan]  {result.status or ''}")
    if result.short_title:
        console.print(result.short_title)


# ---------------------------------------------------------------------------
# paper search / get
# ---------------------------------------------------------------------------


@paper_app.command("search")
def paper_search(
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
    projection: Annotated[
        str | None,
        typer.Option(
            "--projection",
            "-p",
            help="Comma-separated field paths, e.g. referenceCode,phase1.state",
        ),
    ] = None,
) -> None:
    """Search papers."""
    g = _make_glance()
    try:
        result = g.papers.search(
            query=query,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
    except StareError as exc:
        _handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    table = Table(title=f"Papers ({result.total_rows} total)")
    if projection:
        specs = parse_specs(projection)
        for spec in specs:
            table.add_column(spec.header)
        for item in result.results:
            table.add_row(*[_render(resolve(item, s.path)) for s in specs])
    else:
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
    console.print(table)


@paper_app.command("get")
def paper_get(
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
        _handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    ref = result.reference_code or ""
    url = paper_url(ref, web_base=settings.web_base_url) if ref else None
    ref_markup = f"[link={url}]{ref}[/link]" if url else ref
    console.print(f"[bold cyan]{ref_markup}[/bold cyan]  {result.status or ''}")
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
        _handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    ref = result.temp_reference_code or ""
    url = conf_note_url(ref, web_base=settings.web_base_url) if ref else None
    ref_markup = f"[link={url}]{ref}[/link]" if url else ref
    console.print(f"[bold cyan]{ref_markup}[/bold cyan]  {result.status or ''}")
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
        _handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    ref = result.temp_reference_code or ""
    url = pub_note_url(ref, web_base=settings.web_base_url) if ref else None
    ref_markup = f"[link={url}]{ref}[/link]" if url else ref
    console.print(f"[bold cyan]{ref_markup}[/bold cyan]  {result.status or ''}")
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
        _handle_error(exc)
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
        _handle_error(exc)
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
        _handle_error(exc)
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
        _handle_error(exc)
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
