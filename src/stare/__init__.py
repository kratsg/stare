from .version import __version__
from .core import Session
from .settings import settings
from requests import Request


class Glance(object):
    def __init__(self, session=None):
        self.session = session if session else Session()

    @property
    def analyses(self):
        return self.session(Request('GET', 'analyses'))

    @property
    def papers(self):
        return self.session(Request('GET', 'papers'))


__all__ = ['__version__', 'Session', 'settings', 'Glance']
