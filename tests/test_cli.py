import pytest
from click.testing import CliRunner

import time
import betamax

import stare
from stare import commandline


@pytest.fixture(scope='module')
def recorder_session(auth_user):
    commandline.client.user = auth_user
    with betamax.Betamax(
        commandline.client,
        cassette_library_dir=stare.settings.STARE_CASSETTE_LIBRARY_DIR,
    ) as recorder:
        yield recorder


def test_commandline():
    assert commandline.client
    assert commandline.client.user


def test_version():
    runner = CliRunner()
    start = time.time()
    result = runner.invoke(commandline.stare, ['--version'])
    end = time.time()
    elapsed = end - start
    assert result.exit_code == 0
    assert stare.__version__ in result.stdout
    # make sure it took less than a second
    assert elapsed < 1.0


def test_authenticate(recorder_session):
    runner = CliRunner()
    result = runner.invoke(commandline.stare, ['authenticate'])
    assert result.exit_code == 0
    assert 'You have signed in as' in result.output


def test_search_publications(recorder_session):
    recorder_session.use_cassette('test_publications.test_search', record='none')
    runner = CliRunner()
    result = runner.invoke(
        commandline.stare,
        ['search-publications', '--activity-id', 26, '--reference-code', 'HIGG'],
    )
    assert result.exit_code == 0
    assert result.output


def test_publication(recorder_session):
    recorder_session.use_cassette('test_publications.test_get', record='none')
    runner = CliRunner()
    result = runner.invoke(commandline.stare, ['publication', 'HDBS-2018-33'])
    assert result.exit_code == 0
    assert result.output
