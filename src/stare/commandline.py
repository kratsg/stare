import logging
import sys
import click
import json
import os

from .version import __version__
from . import Glance, settings, utilities

logging.basicConfig(format=utilities.FORMAT_STRING, level=logging.INFO)
log = logging.getLogger(__name__)

client = Glance()


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(version=__version__)
@click.option(
    '--username',
    prompt=not (bool(settings.STARE_USERNAME)),
    default=settings.STARE_USERNAME,
    show_default=True,
)
@click.option(
    '--password',
    prompt=not (bool(settings.STARE_PASSWORD)),
    default=settings.STARE_PASSWORD,
    show_default=True,
)
@click.option('--site-url', default=settings.STARE_SITE_URL, show_default=True)
@click.option(
    '--save-auth',
    help='Filename to save authenticated user to for persistence between requests',
    default='.auth',
)
def stare(username, password, site_url, save_auth):
    global client
    os.environ['STARE_USERNAME'] = username
    os.environ['STARE_PASSWORD'] = password
    os.environ['STARE_SITE_URL'] = site_url
    client.session.user._save_auth = save_auth
    client.session.user._load()


@stare.command()
def authenticate():
    client.session.user.authenticate()
    if client.session.user.is_authenticated():
        click.echo(
            "You have signed in as {}(name={}, id={}). Your token expires in {}s.".format(
                client.session.user.username,
                client.session.user.name,
                client.session.user.id,
                client.session.user.expires_in,
            )
        )


@stare.command()
def list_analyses():
    click.echo(json.dumps(client.analyses, indent=2))
    sys.exit(0)


@stare.command()
def list_papers():
    click.echo(json.dumps(client.papers, indent=2))
    sys.exit(0)
