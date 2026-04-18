"""Tests for stare.auth.TokenManager."""

from __future__ import annotations

import base64
import contextlib
import http.client
import json
import threading
import time
import urllib.request
from typing import TYPE_CHECKING
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import filelock
import httpx
import jwt
import pytest
import respx

from stare.auth import TokenManager, _decode_jwt_payload
from stare.exceptions import AuthenticationError, StareError, TokenExpiredError
from stare.models.auth import JwtClaims, ResourceAccessEntry, TokenInfo, _StoredToken
from stare.settings import StareSettings

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def _make_jwt(payload: Mapping[str, object]) -> str:
    """Build a minimal JWT with the given payload (signature is a fake placeholder)."""
    header_b64 = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    )
    return f"{header_b64}.{payload_b64}.fakesig"


# ---------------------------------------------------------------------------
# _decode_jwt_payload
# ---------------------------------------------------------------------------


def test_decode_jwt_payload_returns_known_claims() -> None:
    payload = {
        "sub": "abc123",
        "preferred_username": "kratsg",
        "name": "Test User",
        "email": "test@cern.ch",
        "exp": 9999999999,
        "iat": 1000000000,
    }
    claims = _decode_jwt_payload(_make_jwt(payload))
    assert isinstance(claims, JwtClaims)
    assert claims.sub == "abc123"
    assert claims.preferred_username == "kratsg"
    assert claims.name == "Test User"
    assert claims.email == "test@cern.ch"
    assert claims.exp == 9999999999
    assert claims.iat == 1000000000


def test_decode_jwt_payload_captures_cern_fields() -> None:
    payload = {
        "sub": "han.solo",
        "preferred_username": "han.solo",
        "given_name": "Han",
        "family_name": "Solo",
        "name": "Han Solo",
        "email": "han.solo@star.wars",
        "cern_upn": "han.solo",
        "cern_mail_upn": "han.solo@cern.ch",
        "cern_person_id": "999999",
        "cern_identity_id": "aaaabbbb-test",
        "cern_roles": ["stare-user", "default-role"],
        "eduperson_orcid": "0000-0000-0000-0001",
        "resource_access": {"stare": {"roles": ["stare-user", "default-role"]}},
        "aud": "atlas-glance-analysis-api-dev",
        "typ": "ID",
        "azp": "stare",
    }
    claims = _decode_jwt_payload(_make_jwt(payload))
    assert claims.given_name == "Han"
    assert claims.family_name == "Solo"
    assert claims.cern_upn == "han.solo"
    assert claims.cern_mail_upn == "han.solo@cern.ch"
    assert claims.cern_person_id == "999999"
    assert claims.cern_identity_id == "aaaabbbb-test"
    assert claims.cern_roles == ["stare-user", "default-role"]
    assert claims.eduperson_orcid == "0000-0000-0000-0001"
    assert claims.resource_access["stare"].roles == ["stare-user", "default-role"]
    assert claims.aud == "atlas-glance-analysis-api-dev"
    assert claims.typ == "ID"
    assert claims.azp == "stare"


def test_decode_jwt_payload_preserves_extra_claims() -> None:
    payload = {"sub": "abc", "custom_claim": "custom_value"}
    claims = _decode_jwt_payload(_make_jwt(payload))
    assert claims.sub == "abc"
    assert getattr(claims, "custom_claim", None) == "custom_value"


def test_decode_jwt_payload_returns_empty_on_missing_dot() -> None:
    # No dots → IndexError on [1] → returns empty JwtClaims
    claims = _decode_jwt_payload("invalid-jwt")
    assert isinstance(claims, JwtClaims)
    assert claims.sub is None
    assert claims.preferred_username is None


def test_decode_jwt_payload_returns_empty_on_non_json_payload() -> None:
    # Middle segment decodes to non-JSON bytes
    bad = "header." + base64.urlsafe_b64encode(b"not-json").decode() + ".sig"
    claims = _decode_jwt_payload(bad)
    assert isinstance(claims, JwtClaims)
    assert claims.sub is None


# ---------------------------------------------------------------------------
# get_token_info
# ---------------------------------------------------------------------------


def test_get_token_info_returns_none_when_no_file(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert manager.get_token_info() is None


def test_get_token_info_returns_token_info(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    payload = {"sub": "abc123", "preferred_username": "kratsg"}
    stored = {
        "access_token": "at",
        "id_token": _make_jwt(payload),
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 3600,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(stored))
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    info = manager.get_token_info()
    assert info is not None
    assert isinstance(info, TokenInfo)
    assert info.is_expired is False
    assert info.claims.sub == "abc123"
    assert info.claims.preferred_username == "kratsg"


def test_get_token_info_prefers_id_token_over_access_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    stored = {
        "access_token": _make_jwt({"sub": "from-access"}),
        "id_token": _make_jwt({"sub": "from-id", "preferred_username": "kratsg"}),
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 3600,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(stored))
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    info = manager.get_token_info()
    assert info is not None
    assert info.claims.sub == "from-id"


def test_get_token_info_falls_back_to_access_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    stored = {
        "access_token": _make_jwt(
            {"sub": "from-access", "preferred_username": "kratsg"}
        ),
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 3600,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(stored))
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    info = manager.get_token_info()
    assert info is not None
    assert info.claims.sub == "from-access"


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


def test_logout_removes_token_file(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    with respx.mock:
        respx.post(test_settings.revocation_url).mock(return_value=httpx.Response(200))
        manager = TokenManager(settings=test_settings, token_path=stored_token_path)
        assert stored_token_path.exists()
        manager.logout()
    assert not stored_token_path.exists()


def test_logout_no_op_when_no_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert not tmp_token_path.exists()
    manager.logout()  # must not raise


def test_logout_calls_revocation_for_both_tokens(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    """logout() POSTs to revocation_url for both refresh_token and access_token."""
    with respx.mock:
        revoke_route = respx.post(test_settings.revocation_url).mock(
            return_value=httpx.Response(200)
        )
        manager = TokenManager(settings=test_settings, token_path=stored_token_path)
        manager.logout()
    assert revoke_route.call_count == 2
    assert not stored_token_path.exists()


def test_logout_revocation_sends_correct_params(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    """Each revocation call must include the correct token_type_hint and client_id."""
    with respx.mock:
        revoke_route = respx.post(test_settings.revocation_url).mock(
            return_value=httpx.Response(200)
        )
        manager = TokenManager(settings=test_settings, token_path=stored_token_path)
        manager.logout()

    calls = [
        {k: v[0] for k, v in parse_qs(c.request.content.decode()).items()}
        for c in revoke_route.calls
    ]
    type_hints = {c["token_type_hint"] for c in calls}
    assert type_hints == {"refresh_token", "access_token"}
    for c in calls:
        assert c["client_id"] == test_settings.client_id


def test_logout_completes_when_revocation_unreachable(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    """Revocation is best-effort — logout must complete even on network failure."""
    with respx.mock:
        respx.post(test_settings.revocation_url).mock(
            side_effect=httpx.ConnectError("unreachable")
        )
        manager = TokenManager(settings=test_settings, token_path=stored_token_path)
        manager.logout()  # must not raise
    assert not stored_token_path.exists()


def test_logout_skips_revocation_when_no_stored_tokens(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """If no tokens are stored, the revocation endpoint must not be called."""
    with respx.mock:
        revoke_route = respx.post(test_settings.revocation_url).mock(
            return_value=httpx.Response(200)
        )
        manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
        manager.logout()
    assert not revoke_route.called


# ---------------------------------------------------------------------------
# is_authenticated
# ---------------------------------------------------------------------------


def test_is_authenticated_false_when_no_file(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert manager.is_authenticated() is False


def test_is_authenticated_true_with_valid_token(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=stored_token_path)
    assert manager.is_authenticated() is True


def test_is_authenticated_false_with_expired_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    expired = {
        "access_token": "old",
        "refresh_token": "rt",
        "token_type": "Bearer",
        "expires_at": int(time.time()) - 10,
        "id_token": "id",
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(expired))
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert manager.is_authenticated() is False


def test_is_authenticated_false_with_corrupt_file(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text("not-json{{{")
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert manager.is_authenticated() is False


# ---------------------------------------------------------------------------
# get_token
# ---------------------------------------------------------------------------


def test_get_token_returns_access_token(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=stored_token_path)
    assert manager.get_token() == "test-access-token"


def test_get_token_raises_when_no_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    with pytest.raises(AuthenticationError):
        manager.get_token()


def test_get_token_refreshes_on_expiry(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    expired = {
        "access_token": "old-access",
        "refresh_token": "old-refresh",
        "token_type": "Bearer",
        "expires_at": int(time.time()) - 10,
        "id_token": "old-id",
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(expired))

    new_tokens = {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
        "id_token": "new-id",
    }

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
        token = manager.get_token()

    assert token == "new-access"
    stored = json.loads(tmp_token_path.read_text())
    assert stored["access_token"] == "new-access"
    assert stored["refresh_token"] == "new-refresh"
    assert stored["expires_at"] > int(time.time())


def test_get_token_raises_on_refresh_failure(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    expired = {
        "access_token": "old",
        "refresh_token": "bad-refresh",
        "token_type": "Bearer",
        "expires_at": int(time.time()) - 10,
        "id_token": "id",
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(expired))

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(401, json={"error": "invalid_grant"})
        )
        manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
        with pytest.raises(TokenExpiredError):
            manager.get_token()


def test_get_token_raises_when_no_refresh_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    expired = {
        "access_token": "old",
        "token_type": "Bearer",
        "expires_at": int(time.time()) - 10,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(expired))

    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    with pytest.raises(TokenExpiredError):
        manager.get_token()


# ---------------------------------------------------------------------------
# login (PKCE flow)
# ---------------------------------------------------------------------------


def _make_callback_thread(captured_url: dict[str, str]) -> threading.Thread:
    """Background thread: wait for browser open, then send fake callback."""

    def _run() -> None:
        # Wait until webbrowser.open has been called and URL captured
        deadline = time.time() + 5.0
        while "url" not in captured_url and time.time() < deadline:
            time.sleep(0.01)

        url = captured_url.get("url", "")
        if not url:
            return

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        state = params.get("state", [""])[0]
        redirect_uri = params.get("redirect_uri", [""])[0]
        if not redirect_uri:
            return

        port = urlparse(redirect_uri).port
        callback_url = (
            f"http://127.0.0.1:{port}/callback?code=fake-auth-code&state={state}"
        )
        # Small delay to ensure the server is listening
        time.sleep(0.05)
        with contextlib.suppress(Exception):
            urllib.request.urlopen(callback_url, timeout=5)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


def test_login_stores_tokens(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    captured_url: dict[str, str] = {}

    def _fake_browser(url: str) -> bool:
        captured_url["url"] = url
        return True

    new_tokens = {
        "access_token": "login-access",
        "refresh_token": "login-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
        "id_token": "login-id",
    }

    callback_thread = _make_callback_thread(captured_url)

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with (
            patch("stare.auth.webbrowser.open", side_effect=_fake_browser),
            patch(
                "stare.auth.TokenManager._validate_id_token", return_value=JwtClaims()
            ),
        ):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login()

    callback_thread.join(timeout=5.0)

    assert tmp_token_path.exists()
    stored = json.loads(tmp_token_path.read_text())
    assert stored["access_token"] == "login-access"
    assert stored["refresh_token"] == "login-refresh"
    assert stored["expires_at"] > int(time.time())


def test_login_opens_browser_with_pkce_params(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    captured_url: dict[str, str] = {}

    def _fake_browser(url: str) -> bool:
        captured_url["url"] = url
        return True

    new_tokens = {
        "access_token": "a",
        "refresh_token": "r",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    callback_thread = _make_callback_thread(captured_url)

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with patch("stare.auth.webbrowser.open", side_effect=_fake_browser):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login()

    callback_thread.join(timeout=5.0)

    assert "url" in captured_url
    parsed = urlparse(captured_url["url"])
    assert parsed.scheme + "://" + parsed.netloc + parsed.path == test_settings.auth_url
    params = parse_qs(parsed.query)
    assert params["response_type"] == ["code"]
    assert params["client_id"] == [test_settings.client_id]
    assert params["code_challenge_method"] == ["S256"]
    assert "code_challenge" in params
    assert "state" in params
    assert "redirect_uri" in params


def test_login_calls_on_url_ready_callback(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    captured_url: dict[str, str] = {}
    ready_urls: list[str] = []

    def _fake_browser(url: str) -> bool:
        captured_url["url"] = url
        return True

    def _on_url_ready(url: str) -> None:
        ready_urls.append(url)

    new_tokens = {
        "access_token": "cb-access",
        "refresh_token": "cb-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    callback_thread = _make_callback_thread(captured_url)

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with patch("stare.auth.webbrowser.open", side_effect=_fake_browser):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login(on_url_ready=_on_url_ready)

    callback_thread.join(timeout=5.0)

    assert len(ready_urls) == 1
    assert test_settings.auth_url in ready_urls[0]
    assert "code_challenge" in ready_urls[0]


def test_login_uses_manual_code_fallback(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """get_manual_code() is used when the browser redirect doesn't arrive."""

    def _fake_browser(_url: str) -> bool:
        return True  # pretend to open; no callback will be sent

    def _get_manual_code() -> str | None:
        time.sleep(0.05)  # small delay simulating user typing
        return "manual-auth-code"

    new_tokens = {
        "access_token": "manual-access",
        "refresh_token": "manual-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with patch("stare.auth.webbrowser.open", side_effect=_fake_browser):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login(get_manual_code=_get_manual_code)

    assert tmp_token_path.exists()
    stored = json.loads(tmp_token_path.read_text())
    assert stored["access_token"] == "manual-access"
    assert stored["refresh_token"] == "manual-refresh"


# ---------------------------------------------------------------------------
# _validate_id_token (Step 5)
# ---------------------------------------------------------------------------


def test_validate_id_token_valid(
    test_settings: StareSettings, tmp_token_path: Path
) -> None:
    """_validate_id_token returns JwtClaims when jwt.decode succeeds."""
    payload = {"sub": "user123", "preferred_username": "testuser"}
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    with (
        patch("stare.auth.jwt.PyJWKClient"),
        patch("stare.auth.jwt.decode", return_value=payload),
    ):
        claims = manager._validate_id_token("fake.jwt.token")
    assert claims.sub == "user123"
    assert claims.preferred_username == "testuser"


def test_validate_id_token_expired_raises(
    test_settings: StareSettings, tmp_token_path: Path
) -> None:
    """_validate_id_token raises AuthenticationError on expired token."""
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    with (
        patch("stare.auth.jwt.PyJWKClient"),
        patch(
            "stare.auth.jwt.decode",
            side_effect=jwt.ExpiredSignatureError("Signature has expired"),
        ),
        pytest.raises(AuthenticationError),
    ):
        manager._validate_id_token("fake.jwt.token")


def test_validate_id_token_wrong_issuer_raises(
    test_settings: StareSettings, tmp_token_path: Path
) -> None:
    """_validate_id_token raises AuthenticationError on issuer mismatch."""
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    with (
        patch("stare.auth.jwt.PyJWKClient"),
        patch(
            "stare.auth.jwt.decode",
            side_effect=jwt.InvalidIssuerError("Invalid issuer"),
        ),
        pytest.raises(AuthenticationError),
    ):
        manager._validate_id_token("fake.jwt.token")


def test_validate_id_token_wrong_audience_raises(
    test_settings: StareSettings, tmp_token_path: Path
) -> None:
    """_validate_id_token raises AuthenticationError on audience mismatch."""
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    with (
        patch("stare.auth.jwt.PyJWKClient"),
        patch(
            "stare.auth.jwt.decode",
            side_effect=jwt.InvalidAudienceError("Invalid audience"),
        ),
        pytest.raises(AuthenticationError),
    ):
        manager._validate_id_token("fake.jwt.token")


def test_login_validates_id_token_when_present(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """login() calls _validate_id_token when the OAuth response includes an id_token."""
    captured_url: dict[str, str] = {}

    def _fake_browser(url: str) -> bool:
        captured_url["url"] = url
        return True

    new_tokens = {
        "access_token": "with-id-access",
        "refresh_token": "with-id-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
        "id_token": "some-id-token",
    }

    callback_thread = _make_callback_thread(captured_url)

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with (
            patch("stare.auth.webbrowser.open", side_effect=_fake_browser),
            patch(
                "stare.auth.TokenManager._validate_id_token", return_value=JwtClaims()
            ) as mock_validate,
        ):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login()

    callback_thread.join(timeout=5.0)
    mock_validate.assert_called_once_with("some-id-token")


def test_login_skips_validation_when_no_id_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """login() skips _validate_id_token when the OAuth response has no id_token."""
    captured_url: dict[str, str] = {}

    def _fake_browser(url: str) -> bool:
        captured_url["url"] = url
        return True

    new_tokens = {
        "access_token": "no-id-access",
        "refresh_token": "no-id-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    callback_thread = _make_callback_thread(captured_url)

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with (
            patch("stare.auth.webbrowser.open", side_effect=_fake_browser),
            patch(
                "stare.auth.TokenManager._validate_id_token", return_value=JwtClaims()
            ) as mock_validate,
        ):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login()

    callback_thread.join(timeout=5.0)
    mock_validate.assert_not_called()


# ---------------------------------------------------------------------------
# token exchange (RFC 8693)
# ---------------------------------------------------------------------------


def _exchange_settings(base: StareSettings) -> StareSettings:
    """Return settings identical to *base* but with exchange_audience set."""
    return base.model_copy(update={"exchange_audience": "target-api"})


def test_get_token_with_exchange_calls_token_endpoint(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    """When exchange_audience is set, get_token() performs RFC 8693 exchange."""
    settings = _exchange_settings(test_settings)
    exchanged = {
        "access_token": "exchanged-access",
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    with respx.mock:
        route = respx.post(settings.token_url).mock(
            return_value=httpx.Response(200, json=exchanged)
        )
        manager = TokenManager(settings=settings, token_path=stored_token_path)
        token = manager.get_token()

    assert token == "exchanged-access"
    assert route.called


def test_get_token_without_exchange_skips_endpoint(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    """When exchange_audience is None, get_token() returns the PKCE token directly."""
    with respx.mock:
        manager = TokenManager(settings=test_settings, token_path=stored_token_path)
        token = manager.get_token()
        # No HTTP calls should have been made (respx would raise on unexpected calls)

    assert token == "test-access-token"


def test_get_token_exchange_caches_result(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    """The exchanged token is cached; a second call must not hit the endpoint again."""
    settings = _exchange_settings(test_settings)
    exchanged = {
        "access_token": "cached-exchanged",
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    with respx.mock:
        route = respx.post(settings.token_url).mock(
            return_value=httpx.Response(200, json=exchanged)
        )
        manager = TokenManager(settings=settings, token_path=stored_token_path)
        first = manager.get_token()
        second = manager.get_token()

    assert first == "cached-exchanged"
    assert second == "cached-exchanged"
    assert route.call_count == 1


def test_get_token_exchange_raises_on_http_failure(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    """An HTTP error from the token exchange endpoint raises TokenExpiredError."""
    settings = _exchange_settings(test_settings)
    with respx.mock:
        respx.post(settings.token_url).mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )
        manager = TokenManager(settings=settings, token_path=stored_token_path)
        with pytest.raises(TokenExpiredError):
            manager.get_token()


# ---------------------------------------------------------------------------
# get_pkce_access_token / get_pkce_id_token / get_exchange_access_token
# ---------------------------------------------------------------------------


def test_get_pkce_access_token_returns_stored_token(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=stored_token_path)
    assert manager.get_pkce_access_token() == "test-access-token"


def test_get_pkce_access_token_raises_when_not_logged_in(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    with pytest.raises(AuthenticationError):
        manager.get_pkce_access_token()


def test_get_pkce_id_token_returns_stored_id_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    stored = {
        "access_token": "at",
        "id_token": "my-id-token",
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 3600,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(stored))
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert manager.get_pkce_id_token() == "my-id-token"


def test_get_pkce_id_token_returns_none_when_absent(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    stored = {
        "access_token": "at",
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 3600,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(stored))
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert manager.get_pkce_id_token() is None


def test_get_pkce_id_token_returns_none_when_no_file(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert manager.get_pkce_id_token() is None


def test_get_exchange_access_token_returns_none_when_no_audience(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=stored_token_path)
    assert manager.get_exchange_access_token() is None


def test_get_exchange_access_token_returns_exchanged_token(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    settings = _exchange_settings(test_settings)
    exchanged = {"access_token": "ex-raw", "token_type": "Bearer", "expires_in": 3600}
    with respx.mock:
        respx.post(settings.token_url).mock(
            return_value=httpx.Response(200, json=exchanged)
        )
        manager = TokenManager(settings=settings, token_path=stored_token_path)
        tok = manager.get_exchange_access_token()
    assert tok == "ex-raw"


def test_get_exchange_token_info_returns_none_when_no_audience(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    """Returns None when exchange_audience is not configured."""
    manager = TokenManager(settings=test_settings, token_path=stored_token_path)
    assert manager.get_exchange_token_info() is None


def test_get_exchange_token_info_returns_decoded_claims(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    """Returns a TokenInfo with decoded claims from the exchanged token."""
    settings = _exchange_settings(test_settings)
    payload = {
        "sub": "han.solo",
        "preferred_username": "han.solo",
        "cern_roles": ["stare-user"],
    }
    exchanged = {
        "access_token": _make_jwt(payload),
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    with respx.mock:
        respx.post(settings.token_url).mock(
            return_value=httpx.Response(200, json=exchanged)
        )
        manager = TokenManager(settings=settings, token_path=stored_token_path)
        info = manager.get_exchange_token_info()

    assert info is not None
    assert isinstance(info, TokenInfo)
    assert info.claims.sub == "han.solo"
    assert info.claims.preferred_username == "han.solo"
    assert info.claims.cern_roles == ["stare-user"]
    assert info.is_expired is False


def test_get_exchange_token_info_propagates_auth_error(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """AuthenticationError propagates when not logged in."""
    settings = _exchange_settings(test_settings)
    manager = TokenManager(settings=settings, token_path=tmp_token_path)
    with pytest.raises(AuthenticationError):
        manager.get_exchange_token_info()


def test_resource_access_entry_parses_roles() -> None:
    entry = ResourceAccessEntry.model_validate(
        {"roles": ["stare-user", "default-role"]}
    )
    assert entry.roles == ["stare-user", "default-role"]


def test_resource_access_entry_defaults_empty() -> None:
    entry = ResourceAccessEntry.model_validate({})
    assert entry.roles == []


def test_get_token_exchange_sends_correct_params(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    """The token exchange POST includes the required RFC 8693 fields."""
    settings = _exchange_settings(test_settings)
    exchanged = {
        "access_token": "ex-token",
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    with respx.mock:
        route = respx.post(settings.token_url).mock(
            return_value=httpx.Response(200, json=exchanged)
        )
        manager = TokenManager(settings=settings, token_path=stored_token_path)
        manager.get_token()

    body = route.calls.last.request.content.decode()
    params = {k: v[0] for k, v in parse_qs(body).items()}
    assert params["grant_type"] == "urn:ietf:params:oauth:grant-type:token-exchange"
    assert params["client_id"] == settings.client_id
    assert params["subject_token"] == "test-access-token"
    assert (
        params["subject_token_type"] == "urn:ietf:params:oauth:token-type:access_token"
    )
    assert params["audience"] == "target-api"


# ---------------------------------------------------------------------------
# refresh token rotation safety (Step 3)
# ---------------------------------------------------------------------------


def test_refresh_failure_clears_stored_tokens(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """On HTTP 4xx from the refresh endpoint, stored tokens must be deleted."""
    expired = {
        "access_token": "old",
        "refresh_token": "bad-refresh",
        "token_type": "Bearer",
        "expires_at": int(time.time()) - 10,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(expired))

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(401, json={"error": "invalid_grant"})
        )
        manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
        with pytest.raises(TokenExpiredError):
            manager.get_token()

    assert not tmp_token_path.exists()


def test_refresh_failure_clears_exchange_cache(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """On HTTP 4xx from the refresh endpoint, in-memory exchange cache is cleared."""
    expired = {
        "access_token": "old",
        "refresh_token": "bad-refresh",
        "token_type": "Bearer",
        "expires_at": int(time.time()) - 10,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(expired))

    settings = _exchange_settings(test_settings)
    with respx.mock:
        respx.post(settings.token_url).mock(
            return_value=httpx.Response(401, json={"error": "invalid_grant"})
        )
        manager = TokenManager(settings=settings, token_path=tmp_token_path)
        manager._exchanged_token = "stale-exchanged"
        manager._exchanged_expires_at = int(time.time()) + 3600
        with pytest.raises(TokenExpiredError):
            manager.get_token()

    # Read via typed local vars — prevents mypy from narrowing based on the
    # "stale-exchanged" assignment above and falsely flagging the None check.
    cached_token: str | None = manager._exchanged_token
    assert cached_token is None
    assert manager._exchanged_expires_at == 0


# ---------------------------------------------------------------------------
# concurrent refresh safety (Step 6)
# ---------------------------------------------------------------------------


def test_token_manager_has_thread_lock(
    mock_token_manager: TokenManager,
) -> None:
    """TokenManager has a threading.Lock for in-process safety."""
    assert isinstance(mock_token_manager._thread_lock, type(threading.Lock()))
    assert isinstance(mock_token_manager._file_lock, filelock.FileLock)


def test_file_lock_path_matches_storage_lock_path(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """The file lock path matches the storage backend's lock_path."""

    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    expected = manager._storage.lock_path
    assert manager._file_lock.lock_file == str(expected)


def test_concurrent_get_token_does_not_raise(
    mock_token_manager: TokenManager,
) -> None:
    """Multiple threads calling get_token() simultaneously must not raise."""
    errors: list[Exception] = []

    def _call() -> None:
        try:
            mock_token_manager.get_token()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_call) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
        assert not t.is_alive()

    assert errors == []


# ---------------------------------------------------------------------------
# exchange token expiry + clock skew margin (Step 7)
# ---------------------------------------------------------------------------


def test_is_expired_with_margin_false_when_time_remaining() -> None:
    token = _StoredToken(
        access_token="at", token_type="Bearer", expires_at=int(time.time()) + 300
    )
    assert token.is_expired_with_margin(60) is False
    assert token.is_expired_with_margin(120) is False


def test_is_expired_with_margin_true_within_margin() -> None:
    token = _StoredToken(
        access_token="at", token_type="Bearer", expires_at=int(time.time()) + 30
    )
    assert token.is_expired_with_margin(60) is True  # expires before the 60s margin


def test_is_expired_property_unchanged() -> None:
    """is_expired convenience property still uses 60s margin."""
    valid = _StoredToken(
        access_token="at", token_type="Bearer", expires_at=int(time.time()) + 300
    )
    assert valid.is_expired is False
    almost_expired = _StoredToken(
        access_token="at", token_type="Bearer", expires_at=int(time.time()) + 30
    )
    assert almost_expired.is_expired is True


def test_get_token_uses_configurable_exchange_buffer(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    """get_token() re-exchanges when the buffer exceeds remaining exchange token life."""
    settings = StareSettings(
        **{**test_settings.model_dump(), "exchange_audience": "target-api"}
    )
    exchanged_soon = {
        "access_token": "new-ex",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    manager = TokenManager(settings=settings, token_path=stored_token_path)
    # Seed a cached exchange token that expires in 90s — less than the 120s buffer.
    manager._exchanged_token = "old-ex"
    manager._exchanged_expires_at = int(time.time()) + 90

    with respx.mock:
        respx.post(settings.token_url).mock(
            return_value=httpx.Response(200, json=exchanged_soon)
        )
        token = manager.get_token()

    assert token == "new-ex"


def test_get_base_token_uses_configurable_expiry_margin(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """_get_base_token() triggers refresh when token is within the margin."""
    settings = StareSettings(
        **{**test_settings.model_dump(), "token_expiry_margin_seconds": 300}
    )
    # Token expires in 180s — past 60s default but within the 300s custom margin.
    near_expiry = {
        "access_token": "old",
        "refresh_token": "refresh-me",
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 180,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(near_expiry))

    refreshed = {
        "access_token": "new",
        "refresh_token": "new-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    with respx.mock:
        respx.post(settings.token_url).mock(
            return_value=httpx.Response(200, json=refreshed)
        )
        manager = TokenManager(settings=settings, token_path=tmp_token_path)
        token = manager.get_token()

    assert token == "new"


# ---------------------------------------------------------------------------
# callback server Host header hardening (Step 8)
# ---------------------------------------------------------------------------


def test_callback_handler_rejects_bad_host(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """Callback server returns 403 for requests with unrecognized Host headers."""
    captured_url: dict[str, str] = {}
    bad_host_status: list[int] = []

    def _fake_browser(url: str) -> bool:
        captured_url["url"] = url
        return True

    def _get_manual_code() -> str | None:
        deadline = time.time() + 5.0
        while "url" not in captured_url and time.time() < deadline:
            time.sleep(0.01)
        url = captured_url.get("url", "")
        if not url:
            return None
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        state = params.get("state", [""])[0]
        redirect_uri = params.get("redirect_uri", [""])[0]
        port = urlparse(redirect_uri).port

        time.sleep(0.05)
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.putrequest(
                "GET", f"/callback?code=bad-code&state={state}", skip_host=True
            )
            conn.putheader("Host", "evil.example.com")
            conn.endheaders()
            resp = conn.getresponse()
            bad_host_status.append(resp.status)
            resp.read()
            conn.close()
        except (OSError, http.client.HTTPException):
            pass

        return "manual-code"

    new_tokens = {
        "access_token": "host-check-access",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with patch("stare.auth.webbrowser.open", side_effect=_fake_browser):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login(get_manual_code=_get_manual_code)

    assert bad_host_status == [403]


def test_callback_handler_rejects_non_callback_path(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """Callback server returns 404 for requests to paths other than /callback."""
    captured_url: dict[str, str] = {}
    non_callback_status: list[int] = []

    def _fake_browser(url: str) -> bool:
        captured_url["url"] = url
        return True

    def _get_manual_code() -> str | None:
        deadline = time.time() + 5.0
        while "url" not in captured_url and time.time() < deadline:
            time.sleep(0.01)
        url = captured_url.get("url", "")
        if not url:
            return None
        parsed = urlparse(url)
        redirect_uri = parse_qs(parsed.query).get("redirect_uri", [""])[0]
        port = urlparse(redirect_uri).port

        time.sleep(0.05)
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/favicon.ico")
            resp = conn.getresponse()
            non_callback_status.append(resp.status)
            resp.read()
            conn.close()
        except (OSError, http.client.HTTPException):
            pass

        return "manual-code"

    new_tokens = {
        "access_token": "path-check-access",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with patch("stare.auth.webbrowser.open", side_effect=_fake_browser):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login(get_manual_code=_get_manual_code)

    assert non_callback_status == [404]


def test_token_manager_creates_lock_parent_directory(
    tmp_path: Path, test_settings: StareSettings
) -> None:
    """TokenManager creates the lock file's parent directory if it doesn't exist."""
    token_path = tmp_path / "nested" / "tokens.json"
    manager = TokenManager(settings=test_settings, token_path=token_path)
    assert manager._storage.lock_path.parent.exists()
