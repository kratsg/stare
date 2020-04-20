import os
import pkg_resources

SIMPLE_SETTINGS = {'OVERRIDE_BY_ENV': True}
STARE_USERNAME = ''
STARE_PASSWORD = ''  # nosec
STARE_AUTH_URL = 'https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/'
STARE_SITE_URL = 'https://glance.cern.ch/atlas/analysis/api/'
STARE_CASSETTE_LIBRARY_DIR = 'tests/integration/cassettes'
STARE_CERN_SSL_CHAIN = pkg_resources.resource_filename(
    'stare', os.path.join('data', 'CERN_chain.pem')
)
