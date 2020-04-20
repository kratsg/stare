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
    def publication(self, glance_id):
        req = Request('GET', 'publications/{0:s}'.format(glance_id))
        return self(req)

    def publications(self, activity_id, reference_code):
        req = Request(
            'GET',
            'publications/search',
            params=dict(activityId=activity_id, referenceCode=reference_code),
        )
        return self(req)

    @property
    def analyses(self):
        return self(Request('GET', 'analyses'))

    @property
    def papers(self):
        return self(Request('GET', 'papers'))
