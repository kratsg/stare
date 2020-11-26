import socket
from sys import platform
import stare

import betamax
from betamax_serializers import pretty_json

import pytest

placeholders = {
    'username': stare.settings.STARE_USERNAME,
    'password': stare.settings.STARE_PASSWORD,
}


def filter_bearer_token(interaction, current_cassette):
    # Exit early if the request did not return 200 OK because that's the
    # only time we want to look for Authorization-Token headers
    if interaction.data['response']['status']['code'] != 200:
        return

    headers = interaction.data['request']['headers']
    token = headers.get('Authorization')
    # If there was no token header in the request, exit
    if token is None:
        return

    # Otherwise, create a new placeholder so that when cassette is saved,
    # Betamax will replace the token with our placeholder.
    current_cassette.placeholders.append(
        betamax.cassette.cassette.Placeholder(
            placeholder='Bearer <ACCESS_TOKEN>', replace=token[0]
        )
    )


betamax.Betamax.register_serializer(pretty_json.PrettyJSONSerializer)
with betamax.Betamax.configure() as config:
    config.cassette_library_dir = stare.settings.STARE_CASSETTE_LIBRARY_DIR
    config.default_cassette_options['serialize_with'] = 'prettyjson'
    config.before_record(callback=filter_bearer_token)
    for key, value in placeholders.items():
        config.define_cassette_placeholder('<{}>'.format(key.upper()), replace=value)


@pytest.fixture(scope='session')
def auth_user():
    user = stare.core.User()
    user._jwtOptions = {
        'verify_signature': False,
        'verify_iat': False,
        'verify_exp': False,
    }
    with betamax.Betamax(
        user._session, cassette_library_dir=stare.settings.STARE_CASSETTE_LIBRARY_DIR
    ).use_cassette('test_user.test_user_good_login', record='none'):
        yield user


@pytest.fixture(scope='module')
def auth_session(auth_user):
    yield stare.core.Session(user=auth_user)


# Temporarily work around issue with gethostbyname on OS X
#  - see https://betamax.readthedocs.io/en/latest/long_term_usage.html#known-issues
if platform == 'darwin':
    socket.gethostbyname = lambda x: '127.0.0.1'
