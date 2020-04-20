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
    client.user._save_auth = save_auth
    client.user._load()


@stare.command()
def authenticate():
    client.user.authenticate()
    if client.user.is_authenticated():
        click.echo(
            "You have signed in as {}(name={}, id={}). Your token expires in {}s.".format(
                client.user.username,
                client.user.name,
                client.user.id,
                client.user.expires_in,
            )
        )


@stare.command()
@click.option(
    '--activity-id',
    default=36,
    help='Identification from activities endpoint in SCAB Nominations system.',
)
@click.option(
    '--reference-code',
    default='SUSY',
    help='Code from activities endpoint in SCAB Nominations system.',
)
def search_publications(activity_id, reference_code):
    click.echo(
        json.dumps(
            client.publications(activity_id=activity_id, reference_code=reference_code),
            indent=2,
        )
    )
    sys.exit(0)


@stare.command()
@click.argument('glance-id')
def publication(glance_id):
    """List publication information for GLANCE-ID."""
    click.echo(json.dumps(client.publication(glance_id), indent=2))
    sys.exit(0)
