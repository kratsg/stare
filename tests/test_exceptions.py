"""Tests for the stare exception hierarchy."""

from __future__ import annotations

import pytest

from stare.exceptions import (
    ApiError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    StareError,
    TokenExpiredError,
    UnauthorizedError,
)


class TestExceptionHierarchy:
    def test_stare_error_is_exception(self) -> None:
        assert issubclass(StareError, Exception)

    def test_authentication_error_is_stare_error(self) -> None:
        assert issubclass(AuthenticationError, StareError)

    def test_token_expired_error_is_authentication_error(self) -> None:
        assert issubclass(TokenExpiredError, AuthenticationError)

    def test_api_error_is_stare_error(self) -> None:
        assert issubclass(ApiError, StareError)

    def test_not_found_is_api_error(self) -> None:
        assert issubclass(NotFoundError, ApiError)

    def test_forbidden_is_api_error(self) -> None:
        assert issubclass(ForbiddenError, ApiError)

    def test_unauthorized_is_api_error(self) -> None:
        assert issubclass(UnauthorizedError, ApiError)


class TestApiError:
    def test_attributes(self) -> None:
        err = ApiError(status_code=404, title="Not found", detail="No such resource")
        assert err.status_code == 404
        assert err.title == "Not found"
        assert err.detail == "No such resource"

    def test_str_contains_status_and_title(self) -> None:
        err = ApiError(status_code=403, title="Forbidden", detail="No access")
        assert "403" in str(err)
        assert "Forbidden" in str(err)

    def test_not_found_error(self) -> None:
        err = NotFoundError(status_code=404, title="Not found", detail="Missing")
        assert err.status_code == 404
        assert isinstance(err, ApiError)

    def test_forbidden_error(self) -> None:
        err = ForbiddenError(status_code=403, title="Forbidden", detail="No access")
        assert isinstance(err, ApiError)

    def test_unauthorized_error(self) -> None:
        err = UnauthorizedError(
            status_code=401, title="Unauthorized", detail="Token invalid"
        )
        assert isinstance(err, ApiError)


class TestAuthenticationErrors:
    def test_token_expired_error_message(self) -> None:
        err = TokenExpiredError("Token has expired")
        assert "expired" in str(err).lower()

    def test_authentication_error_raised_as_stare_error(self) -> None:
        msg = "auth failed"
        with pytest.raises(StareError):
            raise AuthenticationError(msg)
