"""Authentication CLI commands."""

from __future__ import annotations

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
def auth_login() -> None:
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
        tm.login(on_url_ready=_on_url_ready, get_manual_code=_get_manual_code)
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    utils.console.print("\n[green]✓[/green] Authenticated successfully.")


@auth_app.command("logout")
def auth_logout() -> None:
    """Remove stored authentication tokens."""
    tm = utils.make_token_manager()
    tm.logout()
    utils.console.print("Logged out.")


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

    utils.console.print(Panel(table, title=panel_title, border_style="blue"))
