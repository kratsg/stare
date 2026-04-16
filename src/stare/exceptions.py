"""Exception hierarchy for stare."""

from __future__ import annotations


class StareError(Exception):
    """Base exception for all stare errors."""


class AuthenticationError(StareError):
    """Authentication failed or no credentials available."""


class TokenExpiredError(AuthenticationError):
    """Stored token is expired; re-run ``stare login``."""


class ApiError(StareError):
    """An error response from the Glance API."""

    def __init__(self, status_code: int, title: str, detail: str) -> None:
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
