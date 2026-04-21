"""Tests for the stare exception hierarchy."""

from __future__ import annotations

import pytest

from stare.exceptions import (
    ApiError,
    AuthenticationError,
    EnrichedErrorResponse,
    ForbiddenError,
    NotFoundError,
    ResponseParseError,
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


class TestResponseParseError:
    def test_is_stare_error(self) -> None:
        assert issubclass(ResponseParseError, StareError)

    def test_message(self) -> None:
        err = ResponseParseError("Failed to parse Foo: field x invalid")
        assert "Failed to parse Foo" in str(err)

    def test_raw_data_defaults_to_none(self) -> None:
        err = ResponseParseError("some error")
        assert err.raw_data is None

    def test_raw_data_stored(self) -> None:
        payload = {"key": "value"}
        err = ResponseParseError("some error", raw_data=payload)
        assert err.raw_data == payload

    def test_details_defaults_to_empty_list(self) -> None:
        err = ResponseParseError("some error")
        assert err.details == []

    def test_details_default_is_not_shared_between_instances(self) -> None:
        err1 = ResponseParseError("err1")
        err2 = ResponseParseError("err2")
        err1.details.append(
            EnrichedErrorResponse(loc=("x",), loc_str="x", message="bad")
        )
        assert err2.details == []

    def test_details_stored_when_provided(self) -> None:
        detail = EnrichedErrorResponse(
            loc=("results", 2),
            loc_str="results[2]",
            message="bad",
        )
        err = ResponseParseError("msg", details=[detail])
        assert err.details == [detail]


class TestAuthenticationErrors:
    def test_token_expired_error_message(self) -> None:
        err = TokenExpiredError("Token has expired")
        assert "expired" in str(err).lower()

    def test_authentication_error_raised_as_stare_error(self) -> None:
        msg = "auth failed"
        with pytest.raises(StareError):
            raise AuthenticationError(msg)
