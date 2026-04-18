"""CLI entry point for stare."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from stare import __version__
from stare._output import stdout_is_interactive
from stare.cli import utils
from stare.cli.analysis import analysis_app
from stare.cli.auth import auth_app
from stare.cli.cache import cache_app
from stare.cli.paper import paper_app
from stare.cli.publications import publications_app
from stare.cli.triggers import triggers_app
from stare.exceptions import StareError
from stare.settings import StareSettings
from stare.urls import conf_note_url, pub_note_url

# Re-export for backward compatibility
sizeof_fmt = utils.sizeof_fmt

app = typer.Typer(
    name="stare",
    help=(
        "ATLAS Glance/Fence API — Python library and CLI.\n\n"
        "Output is a Rich table when stdout is a terminal; structured JSON when piped "
        "or redirected. Use [cyan]--json[/cyan] / [cyan]--no-json[/cyan] to override.\n\n"
        "[bold]Pipe to jq for field selection:[/bold]\n"
        "  [green]stare analysis search | jq '.results[].referenceCode'[/green]"
    ),
    epilog=(
        "[link=https://stare-atlas.readthedocs.io/en/latest/]:blue_book: stare-atlas.rtd.io[/link]\n\n\n\n"
        "[deep_sky_blue1]:copyright: 2026 [link=https://giordonstark.com/]Giordon Stark[/link][/]"
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(auth_app, name="auth")
app.add_typer(analysis_app, name="analysis")
app.add_typer(paper_app, name="paper")
app.add_typer(publications_app, name="publications")
app.add_typer(triggers_app, name="triggers")
app.add_typer(cache_app, name="cache")


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


@app.command()
def version() -> None:
    """Show the stare version."""
    utils.console.print(f"stare {__version__}")


# ---------------------------------------------------------------------------
# conf-note
# ---------------------------------------------------------------------------


@app.command(name="conf-note")
def conf_note(
    ref_code: Annotated[str, typer.Argument(help="CONF note temporary reference code")],
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
) -> None:
    """Fetch a single CONF note by temporary reference code via GET /confnotes/{ref_code}.

    [bold]Examples[/bold]
      [green]stare conf-note ATLAS-CONF-2024-001[/green]
      [green]stare conf-note ATLAS-CONF-2024-001 | jq '.status'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-confnote-getConfNote
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.conf_notes.get(ref_code)
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    ref = result.temp_reference_code or ""
    url = conf_note_url(ref, web_base=settings.web_base_url) if ref else None
    ref_markup = f"[link={url}]{ref}[/link]" if url else ref
    utils.console.print(f"[bold cyan]{ref_markup}[/bold cyan]  {result.status or ''}")
    if result.short_title:
        utils.console.print(result.short_title)


# ---------------------------------------------------------------------------
# pub-note
# ---------------------------------------------------------------------------


@app.command(name="pub-note")
def pub_note(
    ref_code: Annotated[str, typer.Argument(help="PUB note temporary reference code")],
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
) -> None:
    """Fetch a single PUB note by temporary reference code via GET /pubnotes/{ref_code}.

    [bold]Examples[/bold]
      [green]stare pub-note ATL-PHYS-PUB-2024-001[/green]
      [green]stare pub-note ATL-PHYS-PUB-2024-001 | jq '.status'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-pubnote-getPubNote
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.pub_notes.get(ref_code)
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    settings = StareSettings()
    ref = result.temp_reference_code or ""
    url = pub_note_url(ref, web_base=settings.web_base_url) if ref else None
    ref_markup = f"[link={url}]{ref}[/link]" if url else ref
    utils.console.print(f"[bold cyan]{ref_markup}[/bold cyan]  {result.status or ''}")
    if result.short_title:
        utils.console.print(result.short_title)


# ---------------------------------------------------------------------------
# groups / subgroups
# ---------------------------------------------------------------------------


@app.command()
def groups(
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
) -> None:
    """List all leading ATLAS physics groups via GET /groups.

    [bold]Examples[/bold]
      [green]stare groups | jq '.[]'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-groups-getGroups
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.groups.list()
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(json.dumps(result))
        return

    for group in result:
        utils.console.print(group)


@app.command()
def subgroups(
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
) -> None:
    """List all ATLAS physics subgroups via GET /subgroups.

    [bold]Examples[/bold]
      [green]stare subgroups | jq '.[]'[/green]

    [bold]API reference[/bold]
      https://atlas-glance.cern.ch/atlas/analysis/api/docs/#operations-subgroups-getSubgroups
    """
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = g.subgroups.list()
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(json.dumps(result))
        return

    for sg in result:
        utils.console.print(sg)
