"""Provide exception classes for the stare package."""

import sys
import json

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

if sys.version_info[0] == 2:
    from urlparse import urlparse
else:
    from urllib.parse import urlparse


class GlanceDBException(Exception):
    """Base exception class for exceptions that occur within this package."""


class InvalidInvocation(GlanceDBException):
    """Indicate that the code to execute cannot be completed."""


class ResponseException(GlanceDBException):
    """Indicate that there was an error with the completed HTTP request."""

    def __init__(self, response, additional_message=None):
        """Initialize a ResponseException instance.
        :param response: A requests.response instance.
        """
        self.response = response
        message = 'received {} HTTP response'.format(response.status_code)
        try:
            if additional_message is None:
                additional_message = json.dumps(response.json(), indent=2)

        except JSONDecodeError:
            additional_message = response.text.strip()

        if additional_message:
            message = '{}. The following details may help:\n{}'.format(
                message, additional_message
            )
        super(ResponseException, self).__init__(message)


class ExchangeFailure(ResponseException):
    """Indicate that exchanging the access token failed."""


class BadJSON(ResponseException):
    """Indicate the response did not contain valid JSON."""


class BadRequest(ResponseException):
    """Indicate invalid parameters for the request."""


class Conflict(ResponseException):
    """Indicate a conflicting change in the target resource."""


class Forbidden(ResponseException):
    """Indicate the authentication is not permitted for the request."""

    def __init__(self, response):
        additional_message = None
        try:
            additional_message = (
                response.json()
                .get('uuAppErrorMap', {})
                .get('uu-app-workspace/authorization/userIsNotAuthorized', {})
                .get('message', None)
            )
        except JSONDecodeError:
            pass
        super(Forbidden, self).__init__(response, additional_message)


class NotFound(ResponseException):
    """Indicate that the requested URL was not found."""


class Redirect(ResponseException):
    """Indicate the request resulted in a redirect.

    This class adds the attribute ``path``, which is the path to which the
    response redirects.

    """

    def __init__(self, response):
        """Initialize a Redirect exception instance.

        :param response: A requests.response instance containing a location
        header.

        """
        path = urlparse(response.headers['location']).path
        self.path = path[:-5] if path.endswith('.json') else path
        self.response = response
        GlanceDBException.__init__(self, 'Redirect to {}'.format(self.path))


class ServerError(ResponseException):
    """Indicate issues on the server end preventing request fulfillment."""


class SpecialError(ResponseException):
    """Indicate syntax or spam-prevention issues."""

    def __init__(self, response):
        """Initialize a SpecialError exception instance.

        :param response: A requests.response instance containing a message
        and a list of special errors.

        """
        self.response = response

        resp_dict = self.response.json()  # assumes valid JSON
        self.message = resp_dict.get('message', '')
        self.reason = resp_dict.get('reason', '')
        self.special_errors = resp_dict.get('special_errors', [])
        GlanceDBException.__init__(self, 'Special error {!r}'.format(self.message))


class TooLarge(ResponseException):
    """Indicate that the request data exceeds the allowed limit."""


class UnavailableForLegalReasons(ResponseException):
    """Indicate that the requested URL is unavilable due to legal reasons."""


class UnhandledResponse(ResponseException):
    """Indicate a response status code we have not dealt with yet."""
