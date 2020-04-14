import os
import pkg_resources

SIMPLE_SETTINGS = {'OVERRIDE_BY_ENV': True}
STARE_USERNAME = ''
STARE_PASSWORD = ''
STARE_AUTH_URL = 'https://auth.cern.ch/auth/realms/cern/protocol/openid-connect'
STARE_SITE_URL = 'https://glance-stage.cern.ch/release/frapi/atlas/analysis/api'
STARE_JWKS_URL = 'https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/certs'
STARE_CASSETTE_LIBRARY_DIR = 'tests/integration/cassettes'
STARE_CERN_SSL_CHAIN = pkg_resources.resource_filename(
    __name__, os.path.join('data', 'CERN_chain.pem')
)
