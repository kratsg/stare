import logging
import requests
from requests.status_codes import codes
import cachecontrol.caches.file_cache
from cachecontrol import CacheControlAdapter, CacheController
from cachecontrol.heuristics import ExpiresAfter

from jose import jwt
import time
import os
import pickle  # nosec

from .settings import settings
from . import exceptions

log = logging.getLogger(__name__)


class User(object):
    def __init__(
        self,
        username=settings.STARE_USERNAME,
        password=settings.STARE_PASSWORD,
        audience='stare',
        jwtOptions={},
        save_auth=None,
    ):

        # session handling (for injection in tests)
        self._session = requests.Session()
        # store last call to authenticate
        self._response = None
        self._status_code = None
        # store jwks for validation/verification
        self._jwks = None
        # store information after authorization occurs
        self._subject_token = None
        self._access_token = None
        self._raw_id_token = None
        self._id_token = None
        # initialization configuration
        self._username = username
        self._password = password
        self._audience = audience
        self._jwtOptions = jwtOptions
        # serialization/persistence
        self._save_auth = save_auth
        self._load()

    def _load(self):
        if self._save_auth and os.path.isfile(self._save_auth):
            try:
                saved_user = pickle.load(open(self._save_auth, 'rb'))  # nosec
                if saved_user.is_expired():
                    log.warning(
                        "Expired saved user session in {}. Creating a new one.".format(
                            self._save_auth
                        )
                    )
                    return False
                if saved_user.is_authenticated():
                    self.__dict__.update(saved_user.__dict__)
                    return True
                return False
            except pickle.UnpicklingError:
                log.warning(
                    "Unable to load user session from {}. Creating a new one.".format(
                        self._save_auth
                    )
                )
            except KeyError:  # python2 specific error
                log.warning(
                    "Unable to load user session from {}. Creating a new one.".format(
                        self._save_auth
                    )
                )
            return False

    def _dump(self):
        if self.is_authenticated() and not self.is_expired() and self._save_auth:
            try:
                pickle.dump(self, open(self._save_auth, 'wb'), pickle.HIGHEST_PROTOCOL)
                return True
            except pickle.PicklingError:
                log.warning(
                    "Unable to save user session to {}.".format(self._save_auth)
                )
            return False

    def _load_jwks(self, force=False):
        if self._jwks is None or force:
            self._jwks = self._session.get(
                requests.compat.urljoin(settings.STARE_AUTH_URL, 'certs')
            ).json()

    def _parse_id_token(self):
        if self._id_token:
            self._load_jwks()
            self._id_token = jwt.decode(
                self._id_token,
                self._jwks,
                algorithms='RS256',
                audience=self._audience,
                options=self._jwtOptions,
                access_token=self._subject_token,
            )

    def _exchange_token(self):
        # should only be called from within authenticate
        response = self._session.post(
            requests.compat.urljoin(settings.STARE_AUTH_URL, 'token'),
            data={
                'client_id': 'stare',
                'audience': 'atlas-analysis-api',
                'subject_token': self._subject_token,
                'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
                'requested_token_type': 'urn:ietf:params:oauth:token-type:access_token',
            },
        )
        if response.status_code != 200:
            raise exceptions.ExchangeFailure(response)
        self._access_token = response.json()['access_token']

    def authenticate(self):
        # if not expired, do nothing
        if self.is_authenticated():
            return True
        # session-less request
        response = self._session.post(
            requests.compat.urljoin(settings.STARE_AUTH_URL, 'token'),
            data={
                'username': self._username,
                'password': self._password,
                'grant_type': 'password',
                'scope': 'openid',
                'client_id': 'stare',
            },
        )

        self._response = response.json()
        self._status_code = response.status_code
        self._subject_token = self._response.get('access_token')
        self._raw_id_token = self._response.get('id_token')
        self._id_token = self._raw_id_token

        # handle parsing the id token
        self._parse_id_token()

        if not self.is_authenticated():
            log.warning(
                'Authorization failed. Message: {}'.format(
                    self._response['error_description']
                )
            )
        else:
            self._exchange_token()
            self._dump()

    @property
    def subject_token(self):
        return self._subject_token

    @property
    def access_token(self):
        return self._access_token

    @property
    def id_token(self):
        return self._id_token if self._id_token else {}

    @property
    def id(self):
        return self.id_token.get('cern_person_id', '')

    @property
    def username(self):
        return self.id_token.get('cern_upn', '')

    @property
    def name(self):
        return self.id_token.get('name', '')

    @property
    def email(self):
        return self.id_token.get('email', '')

    @property
    def orcid(self):
        return self.id_token.get('eduperson_orcid', '')

    @property
    def permissions(self):
        return self.id_token.get('permissions', [])

    @property
    def egroups(self):
        return self.id_token.get('egroups', [])

    @property
    def usergroups(self):
        return self.id_token.get('usergroups', [])

    @property
    def expires_at(self):
        return self.id_token.get('exp', 0)

    @property
    def expires_in(self):
        expires_in = self.expires_at - time.time()
        return 0 if expires_in < 0 else int(expires_in)

    @property
    def bearer(self):
        return self.access_token if self.access_token else ''

    def is_authenticated(self):
        return bool(
            self._status_code == codes['ok']
            and self._subject_token
            and self._raw_id_token
        )

    def is_expired(self):
        return not (self.expires_in > 0)

    def __repr__(self):
        return "{0:s}(name={1:s}, expires_in={2:d}s)".format(
            self.__class__.__name__, self.name, self.expires_in
        )


class Session(requests.Session):
    STATUS_EXCEPTIONS = {
        codes['bad_gateway']: exceptions.ServerError,
        codes['bad_request']: exceptions.BadRequest,
        codes['conflict']: exceptions.Conflict,
        codes['found']: exceptions.Redirect,
        codes['forbidden']: exceptions.Forbidden,
        codes['gateway_timeout']: exceptions.ServerError,
        codes['internal_server_error']: exceptions.ServerError,
        codes['media_type']: exceptions.SpecialError,
        codes['not_found']: exceptions.NotFound,
        codes['request_entity_too_large']: exceptions.TooLarge,
        codes['service_unavailable']: exceptions.ServerError,
        codes['unauthorized']: exceptions.Forbidden,
        codes['unavailable_for_legal_reasons']: exceptions.UnavailableForLegalReasons,
    }
    SUCCESS_STATUSES = {codes['created'], codes['ok']}

    def __init__(
        self,
        user=None,
        prefix_url=settings.STARE_SITE_URL,
        save_auth=None,
        cache=cachecontrol.caches.file_cache.FileCache('.webcache'),
        expires_after=None,
    ):
        """
        user (stare.core.User): A user object. Create one if not specified.
        prefix_url (str): The prefix url to use for all requests.
        save_auth (str): A file path to where to save authentication information.
        cache (str): A CacheControl.caches object for cache (default: cachecontrol.caches.file_cache.FileCache)
        expires_after (dict): The arguments are the same as the datetime.timedelta object. This will override or add the Expires header and override or set the Cache-Control header to public.
        """
        super(Session, self).__init__()
        self.user = user if user else User(save_auth=save_auth)
        self.auth = self._authorize
        self.prefix_url = prefix_url
        # store last call
        self._response = None

        cache_options = {'controller_class': CacheController}
        if cache:
            cache_options.update(dict(cache=cache))
        # handle expirations for cache
        if expires_after and isinstance(expires_after, dict):
            cache_options.update(dict(heuristic=ExpiresAfter(**expires_after)))
        if cache_options:
            # add caching
            super(Session, self).mount(
                self.prefix_url, CacheControlAdapter(**cache_options)
            )

    def _authorize(self, req):
        self.user.authenticate()
        req.headers.update({'Authorization': 'Bearer {0:s}'.format(self.user.bearer)})
        return req

    def _normalize_url(self, url):
        return requests.compat.urljoin(self.prefix_url, url)

    def _check_response(self, response):
        if response.status_code in self.STATUS_EXCEPTIONS:
            raise self.STATUS_EXCEPTIONS[response.status_code](response)

        try:
            response.raise_for_status()
        except:
            raise exceptions.UnhandledResponse(response)

    def prepare_request(self, request):
        request.url = self._normalize_url(request.url)
        return super(Session, self).prepare_request(request)

    def send(self, request, **kwargs):
        response = super(Session, self).send(request, **kwargs)
        self._response = response
        log.debug(
            'Response: {} ({} bytes)'.format(
                response.status_code, response.headers.get('content-length')
            )
        )
        self._check_response(response)
        return response

    def request(self, method, url, *args, **kwargs):
        url = self._normalize_url(url)
        return super(Session, self).request(method, url, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        if len(args) == 1:
            return self.send(self.prepare_request(*args), **kwargs)
        else:
            return self.request(*args, **kwargs)
