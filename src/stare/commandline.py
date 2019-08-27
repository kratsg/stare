import logging
import sys
import click
import json
import os

from .version import __version__
from . import core
from . import settings
from . import utilities

logging.basicConfig(format=utilities.FORMAT_STRING, level=logging.INFO)
log = logging.getLogger(__name__)

_session = core.Session()


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(version=__version__)
@click.option(
    '--apiKey',
    prompt=not (bool(settings.GLANCE_API_KEY)),
    default=settings.GLANCE_API_KEY,
    show_default=True,
)
@click.option('--site-url', default=settings.SITE_URL, show_default=True)
@click.option(
    '--save-auth',
    help='Filename to save authenticated user to for persistence between requests',
)
def stare(apikey, site_url, save_auth):
    global _session
    os.environ['GLANCE_API_KEY'] = apikey
    os.environ['SITE_URL'] = site_url
    _session.user._save_auth = save_auth
    _session.user._load()


@stare.command()
def authenticate():
    _session.user.authorize()
    if _session.user.is_authorized():
        click.echo(
            "You have signed in as {}(id={}). Your token expires in {}s.\n\t- permissions: {}\n\t- egroups: {}\n\t- usergroups: {}".format(
                _session.user.name,
                _session.user.id,
                _session.user.expires_in,
                _session.user.permissions,
                _session.user.egroups,
                _session.user.usergroups,
            )
        )


@stare.command()
def list_analyses():
    click.echo(json.dumps(_session.get("analyses"), indent=2))
    sys.exit(0)


@stare.command()
def list_papers():
    click.echo(json.dumps(_session.get('papers'), indent=2))
    sys.exit(0)
