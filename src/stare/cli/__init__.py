"""CLI entry point for stare."""

from __future__ import annotations

import typer

from stare import __version__
from stare.cli import utils
from stare.cli.analysis import analysis_app
from stare.cli.auth import auth_app
from stare.cli.cache import cache_app
from stare.cli.confnote import confnote_app
from stare.cli.leadgroup import leadgroup_app
from stare.cli.paper import paper_app
from stare.cli.publications import publications_app
from stare.cli.pubnote import pubnote_app
from stare.cli.subgroup import subgroup_app
from stare.cli.triggers import triggers_app

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
        "[deep_sky_blue1]:copyright: 2019 [link=https://giordonstark.com/]Giordon Stark[/link][/]"
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(auth_app, name="auth")
app.add_typer(analysis_app, name="analysis")
app.add_typer(paper_app, name="paper")
app.add_typer(confnote_app, name="confnote")
app.add_typer(pubnote_app, name="pubnote")
app.add_typer(publications_app, name="publications")
app.add_typer(leadgroup_app, name="leadgroups")
app.add_typer(subgroup_app, name="subgroups")
app.add_typer(triggers_app, name="triggers")
app.add_typer(cache_app, name="cache")


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


@app.command()
def version() -> None:
    """Show the stare version."""
    utils.console.print(f"stare {__version__}")
