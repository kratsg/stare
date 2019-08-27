from dotenv import load_dotenv
import pkg_resources

load_dotenv()

import os

try:
    from types import SimpleNamespace
except:
    from argparse import Namespace as SimpleNamespace

settings = SimpleNamespace(
    GLANCE_API_KEY=os.getenv('GLANCE_API_KEY', ''),
    SITE_URL=os.getenv(
        'SITE_URL',
        'https://glance-stage.cern.ch/release/frapi/atlas/analysis/api/public/',
    ),
    CASSETTE_LIBRARY_DIR=os.getenv(
        'CASSETTE_LIBRARY_DIR', 'tests/integration/cassettes'
    ),
    CERN_SSL_CHAIN=os.getenv(
        'CERN_SSL_CHAIN',
        pkg_resources.resource_filename(
            __name__, os.path.join('data', 'CERN_chain.pem')
        ),
    ),
)
