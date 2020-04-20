from .core import Session
from . import exceptions
from requests import Request


class Client(Session):
    def send(self, request, **kwargs):
        response = super(Client, self).send(request, **kwargs)

        if response.headers.get('content-length') == '0':
            return {}
        try:
            data = response.json()
        except ValueError:
            raise exceptions.BadJSON(response)

        return data


class Glance(Client):
    @property
    def analyses(self):
        return self(Request('GET', 'analyses'))

    @property
    def papers(self):
        return self(Request('GET', 'papers'))
