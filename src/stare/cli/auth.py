"""Authentication CLI commands."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from stare.cli import utils
from stare.exceptions import StareError

auth_app = typer.Typer(help="Authentication commands.", rich_markup_mode="rich")


@auth_app.command("login")
def auth_login(
    offline: Annotated[
        bool,
        typer.Option(
            "--offline",
            help="Request an offline session that survives SSO logout, for cron/CI use",
        ),
    ] = False,
) -> None:
    """Authenticate with CERN SSO using OAuth2 PKCE."""
    tm = utils.make_token_manager()

    def _on_url_ready(url: str) -> None:
        utils.console.print(
            Panel(
                f"[dim]If your browser did not open, copy this URL:[/dim]\n\n"
                f"[bold cyan][link={url}]{url}[/link][/bold cyan]",
                title="[bold]CERN SSO Authentication[/bold]",
                border_style="blue",
                padding=(1, 2),
            ),
            crop=False,
        )
        utils.console.print("[dim]Opening browser...[/dim]")

    def _get_manual_code() -> str | None:
        utils.console.print()
        utils.console.print(
            "[dim]If the redirect did not complete automatically, find the[/dim]\n"
            "[dim][bold]code=[/bold] value in the redirect URL and paste it below.[/dim]\n"
            "[dim](Press Enter to keep waiting for the automatic redirect.)[/dim]"
        )
        raw = typer.prompt("Authorization code", default="", show_default=False)
        return raw.strip() or None

    try:
        tm.login(
            on_url_ready=_on_url_ready,
            get_manual_code=_get_manual_code,
            offline=offline,
        )
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    utils.console.print("\n[green]✓[/green] Authenticated successfully.")
    if offline:
        utils.console.print(
            "[dim]Offline session stored. To run stare on another host, use "
            "[bold]stare auth export[/bold] | ... [bold]stare auth import[/bold].[/dim]"
        )


@auth_app.command("logout")
def auth_logout() -> None:
    """Remove stored authentication tokens."""
    tm = utils.make_token_manager()
    try:
        tm.logout()
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc
    utils.console.print("Logged out.")


@auth_app.command("export")
def auth_export(
    move: Annotated[
        bool,
        typer.Option("--move", help="Delete the local copy after exporting"),
    ] = False,
) -> None:
    """Print the offline refresh token, for [bold]stare auth import[/bold] on another host."""
    tm = utils.make_token_manager()
    try:
        token = tm.export_refresh_token(move=move)
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc
    typer.echo(token)
    utils.err_console.print(
        "[yellow]Keep this token secret[/yellow] — it grants API access as you. "
        "Refresh tokens rotate, so use the session on one host only."
    )
    if move:
        utils.err_console.print("Local copy deleted.")
    else:
        utils.err_console.print(
            "[dim]The copy on this host may stop working once the other host "
            "refreshes; pass [bold]--move[/bold] to delete it.[/dim]"
        )


@auth_app.command("import")
def auth_import() -> None:
    """Store an offline session from a refresh token read on stdin."""
    tm = utils.make_token_manager()
    if sys.stdin.isatty():
        raw = typer.prompt("Refresh token", hide_input=True)
    else:
        raw = sys.stdin.read()
    try:
        tm.import_refresh_token(raw)
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc
    utils.console.print("[green]✓[/green] Imported offline session.")


@auth_app.command("status")
def auth_status() -> None:
    """Show current authentication status (quick check)."""
    tm = utils.make_token_manager()
    if tm.is_authenticated():
        utils.console.print("[green]Authenticated[/green]")
    else:
        utils.console.print(
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
    tm = utils.make_token_manager()

    # --exchange --id-token is nonsensical: token exchange produces no id token
    if exchange and id_token:
        utils.err_console.print(
            "The RFC 8693 token exchange does not produce an id token."
        )
        raise typer.Exit(1)

    # Raw token output mode: print token string(s) and return
    if access_token or id_token:
        if access_token:
            if exchange:
                try:
                    tok = tm.get_exchange_access_token()
                except StareError as exc:
                    utils.handle_error(exc)
                    raise typer.Exit(1) from exc
                if tok is None:
                    utils.err_console.print(
                        "Token exchange is not configured. "
                        "Set [bold]STARE_EXCHANGE_AUDIENCE[/bold] to enable."
                    )
                    raise typer.Exit(1)
            else:
                try:
                    tok = tm.get_pkce_access_token()
                except StareError as exc:
                    utils.handle_error(exc)
                    raise typer.Exit(1) from exc
            typer.echo(tok)
        if id_token:
            raw = tm.get_pkce_id_token()
            if raw is None:
                utils.err_console.print("No id token is stored.")
                raise typer.Exit(1)
            typer.echo(raw)
        return

    session = None
    if exchange:
        try:
            info = tm.get_exchange_token_info()
        except StareError as exc:
            utils.handle_error(exc)
            raise typer.Exit(1) from exc
        if info is None:
            utils.err_console.print(
                "Token exchange is not configured. "
                "Set [bold]STARE_EXCHANGE_AUDIENCE[/bold] to enable."
            )
            raise typer.Exit(1)
        panel_title = "[bold]Exchange Token Info[/bold]"
    else:
        info = tm.get_token_info()
        if info is None:
            utils.err_console.print(
                "Not authenticated. Run [bold]stare auth login[/bold] to authenticate."
            )
            raise typer.Exit(1)
        panel_title = "[bold]Auth Info[/bold]"
        session = tm.get_session_info()

    exp: int = info.expires_at
    now = int(time.time())
    claims = info.claims

    # Derive the label from the real expiry vs now (not info.is_expired, which
    # bakes in a 60s refresh margin) so the state matches the shown timestamp.
    remaining = exp - now
    expires_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
    ts = expires_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    if remaining > 60:
        mins, secs = divmod(remaining, 60)
        expiry_label = f"[green]valid[/green] — expires in {mins}m {secs}s ({ts})"
    elif remaining > 0:
        expiry_label = (
            f"[yellow]expiring soon[/yellow] — expires in {remaining}s ({ts})"
        )
    else:
        expiry_label = f"[red]expired[/red] ({ts})"

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

    if session is not None:
        if session.offline:
            # Keycloak offline tokens carry no exp; the server-side idle
            # timeout (not visible to the client) decides when they lapse.
            session_label = (
                "[green]offline[/green] — no fixed expiry; lapses if unused "
                "past the server's idle timeout"
            )
        elif session.refresh_expires_at is not None:
            refresh_dt = datetime.fromtimestamp(
                session.refresh_expires_at, tz=timezone.utc
            )
            session_label = (
                f"online — refresh expires {refresh_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} "
                "or at SSO logout"
            )
        else:
            session_label = "online — ends with your SSO session"
        table.add_row("Session", session_label)

    utils.console.print(Panel(table, title=panel_title, border_style="blue"))
