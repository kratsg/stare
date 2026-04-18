"""Exception hierarchy for stare."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class StareError(Exception):
    """Base exception for all stare errors."""


class AuthenticationError(StareError):
    """Authentication failed or no credentials available."""


class TokenExpiredError(AuthenticationError):
    """Stored token is expired; re-run ``stare login``."""


class ApiError(StareError):
    """An error response from the Glance API."""

    def __init__(self, status_code: int, title: str, detail: str) -> None:
        """Store HTTP status code, title, and detail then delegate to Exception."""
        self.status_code = status_code
        self.title = title
        self.detail = detail
        super().__init__(f"[{status_code}] {title}: {detail}")


class NotFoundError(ApiError):
    """The requested resource was not found (404)."""


class ForbiddenError(ApiError):
    """The request is forbidden (403)."""


class UnauthorizedError(ApiError):
    """Authentication token is missing or invalid (401)."""


class ResponseParseError(StareError):
    """Raised when an API response cannot be parsed into the expected model.

    Attributes:
        raw_data: The raw object that failed validation (typically the parsed
            JSON dict/list), attached so callers can display it alongside the
            error message.
    """

    def __init__(self, message: str, raw_data: Any = None) -> None:
        """Store the raw API payload alongside the error message."""
        self.raw_data = raw_data
        super().__init__(message)
