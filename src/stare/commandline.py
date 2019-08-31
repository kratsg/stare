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
    '--apiKey',
    prompt=not (bool(settings.GLANCE_API_KEY)),
    default=settings.GLANCE_API_KEY,
    show_default=True,
)
@click.option('--site-url', default=settings.SITE_URL, show_default=True)
@click.option(
    '--save-auth',
    help='Filename to save authenticated user to for persistence between requests',
    default='.auth',
)
def stare(apikey, site_url, save_auth):
    global client
    os.environ['GLANCE_API_KEY'] = apikey
    os.environ['SITE_URL'] = site_url
    client.session.user._save_auth = save_auth
    client.session.user._load()


@stare.command()
def authenticate():
    client.session.user.authenticate()
    if client.session.user.is_authenticated():
        click.echo(
            "You have signed in as {}(id={}). Your token expires in {}s.\n\t- permissions: {}\n\t- egroups: {}\n\t- usergroups: {}".format(
                client.session.user.name,
                client.session.user.id,
                client.session.user.expires_in,
                client.session.user.permissions,
                client.session.user.egroups,
                client.session.user.usergroups,
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
