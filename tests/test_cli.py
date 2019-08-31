import pytest
from click.testing import CliRunner

import time
import betamax

import stare
from stare import commandline


@pytest.fixture(scope='module')
def recorder_session(auth_user):
    commandline.client.session.user = auth_user
    with betamax.Betamax(
        commandline.client.session,
        cassette_library_dir=stare.settings.CASSETTE_LIBRARY_DIR,
    ) as recorder:
        yield recorder


def test_commandline():
    assert commandline.client.session
    assert commandline.client.session.user


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


def test_list_analyses(recorder_session):
    recorder_session.use_cassette('test_analysis.test_get', record='none')
    runner = CliRunner()
    result = runner.invoke(commandline.stare, ['list-analyses'])
    assert result.exit_code == 0
    assert result.output


def test_list_papers(recorder_session):
    recorder_session.use_cassette('test_paper.test_get', record='none')
    runner = CliRunner()
    result = runner.invoke(commandline.stare, ['list-papers'])
    assert result.exit_code == 0
    assert result.output
